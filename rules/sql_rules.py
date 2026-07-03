"""SQL recommendation rules SQL-001 through SQL-006 (PRD §16).

Every rule is a pure function:
    rule_sql_NNN(
        entities: list[EntityInfo],
        relationships: list[RelationshipInfo],
        database_type: str = "sqlite",
    ) -> list[Finding]

run_all_sql_rules(result) calls all six and attaches findings to the result.
"""
from __future__ import annotations

import re
from typing import Sequence

from models.schema_models import (
    AnalysisResult,
    EntityInfo,
    FieldInfo,
    Finding,
    RelationshipInfo,
)

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _tables(entities: Sequence[EntityInfo]) -> list[EntityInfo]:
    return [e for e in entities if e.entity_type == "table"]


def _fk_indexed(field: FieldInfo, entity: EntityInfo) -> bool:
    """Return True if *field* is the leading column of at least one index."""
    for idx in entity.indexes:
        cols = idx.get("columns") or []
        if cols and cols[0] == field.name:
            return True
    return False


def _detect_convention(name: str) -> str:
    """Classify *name* as 'snake', 'camel', 'pascal', or 'other'."""
    if re.fullmatch(r"[a-z][a-z0-9]*(_[a-z0-9]+)*", name):
        return "snake"
    if re.fullmatch(r"[a-z][a-zA-Z0-9]*", name) and re.search(r"[A-Z]", name):
        return "camel"
    if re.fullmatch(r"[A-Z][a-zA-Z0-9]*", name):
        return "pascal"
    return "other"


# Patterns for SQL-005 suspicious-type detection
_DATE_NAME_RE = re.compile(
    r"(^date_|_date$|_at$|_time$|_ts$|_timestamp$|_datetime$)", re.IGNORECASE
)
_NUMERIC_NAME_RE = re.compile(
    r"(_amount$|_price$|_cost$|_salary$|_count$|_total$|_qty$|_quantity$|_fee$|_rate$|_sum$)",
    re.IGNORECASE,
)
_BOOL_NAME_RE = re.compile(
    r"(^is_|^has_|^can_|^should_|^was_|^will_)", re.IGNORECASE
)

# For SQL-003 candidate detection
_ID_SUFFIX_RE = re.compile(r"^(.+)_id$", re.IGNORECASE)
_CAMEL_ID_RE = re.compile(r"^(.+)Id$")


def _candidate_table_names(field_name: str) -> list[str]:
    """Return possible target table names for an undeclared FK field."""
    m = _ID_SUFFIX_RE.match(field_name)
    if m:
        base = m.group(1).lower()
        return [base, base + "s", base + "es"]
    m = _CAMEL_ID_RE.match(field_name)
    if m:
        base = m.group(1).lower()
        return [base, base + "s", base + "es"]
    return []


def _inferred_confidence(
    name_match: bool,
    types_match: bool,
    target_has_pk: bool,
) -> float:
    """Confidence formula from PRD §18.3 (without value-overlap — Milestone 2)."""
    score = 0
    if name_match:
        score += 35
    if types_match:
        score += 20
    if target_has_pk:
        score += 20
    return score / 100.0


# ---------------------------------------------------------------------------
# SQL-001 — Missing primary key
# ---------------------------------------------------------------------------

def rule_sql_001(
    entities: Sequence[EntityInfo],
    relationships: Sequence[RelationshipInfo],
    database_type: str = "sqlite",
) -> list[Finding]:
    """Fire when a physical table has no declared primary key."""
    referenced_tables = {r.target_entity for r in relationships}
    findings: list[Finding] = []

    for entity in _tables(entities):
        pk_fields = [f for f in entity.fields if f.primary_key]
        if pk_fields:
            continue

        severity = "high" if entity.name in referenced_tables else "medium"
        unique_cols = [f.name for f in entity.fields if f.unique]
        evidence = [f"Table '{entity.name}' has no declared primary key."]
        if unique_cols:
            evidence.append(f"Existing unique columns that could serve as a key: {', '.join(unique_cols)}.")
        if entity.name in referenced_tables:
            evidence.append("This table is referenced by a foreign key — missing PK increases integrity risk.")

        findings.append(Finding(
            rule_id="SQL-001",
            database_type=database_type,
            entity=entity.name,
            severity=severity,
            title="Missing primary key",
            description=f"Table '{entity.name}' has no declared primary key.",
            evidence=evidence,
            impact=(
                "Rows cannot be uniquely identified. "
                "Duplicate rows may be introduced and referential integrity cannot be enforced."
            ),
            recommendation=(
                "Review whether the table has a stable natural key. "
                "Consider adding a primary key after verifying uniqueness and application compatibility."
            ),
        ))

    return findings


# ---------------------------------------------------------------------------
# SQL-002 — Foreign-key column without index
# ---------------------------------------------------------------------------

def rule_sql_002(
    entities: Sequence[EntityInfo],
    relationships: Sequence[RelationshipInfo],
    database_type: str = "sqlite",
) -> list[Finding]:
    """Fire when a declared FK column is not the leading column of any index."""
    findings: list[Finding] = []

    for entity in _tables(entities):
        for field in entity.fields:
            if not field.foreign_key_target:
                continue
            if _fk_indexed(field, entity):
                continue

            target = field.foreign_key_target
            existing_idx = [idx["name"] for idx in entity.indexes] if entity.indexes else []
            evidence = [
                f"Column '{field.name}' is a foreign key referencing '{target}'.",
                "No index has this column as its leading entry.",
            ]
            if existing_idx:
                evidence.append(f"Existing indexes on '{entity.name}': {', '.join(existing_idx)}.")
            else:
                evidence.append(f"Table '{entity.name}' has no indexes at all.")

            findings.append(Finding(
                rule_id="SQL-002",
                database_type=database_type,
                entity=entity.name,
                field=field.name,
                severity="medium",
                title="Foreign-key column without index",
                description=(
                    f"'{entity.name}.{field.name}' is a declared foreign key "
                    f"but is not covered by a leading index."
                ),
                evidence=evidence,
                impact=(
                    "JOIN, UPDATE, and DELETE operations that filter on this column "
                    "may perform a full table scan."
                ),
                recommendation=(
                    "Review join and delete patterns on this column. "
                    "Consider adding an index when the column is frequently used for lookups."
                ),
                suggested_command=(
                    f"CREATE INDEX idx_{entity.name}_{field.name} "
                    f"ON {entity.name}({field.name});"
                ),
            ))

    return findings


# ---------------------------------------------------------------------------
# SQL-003 — Possible undeclared relationship
# ---------------------------------------------------------------------------

def rule_sql_003(
    entities: Sequence[EntityInfo],
    relationships: Sequence[RelationshipInfo],
    database_type: str = "sqlite",
) -> list[Finding]:
    """Fire when a column looks like a FK by name but has no declared constraint."""
    # Build lookup: table_name (lower) → EntityInfo
    table_map: dict[str, EntityInfo] = {
        e.name.lower(): e for e in _tables(entities)
    }
    # Already-declared FK pairs to avoid duplicates
    declared = {
        (r.source_entity.lower(), r.source_field.lower())
        for r in relationships
        if r.declared
    }

    findings: list[Finding] = []

    for entity in _tables(entities):
        for field in entity.fields:
            # Skip if already an FK or not an _id/_Id column
            if field.foreign_key_target:
                continue
            if (entity.name.lower(), field.name.lower()) in declared:
                continue

            candidates = _candidate_table_names(field.name)
            if not candidates:
                continue

            target_entity: EntityInfo | None = None
            for cand in candidates:
                if cand in table_map and cand != entity.name.lower():
                    target_entity = table_map[cand]
                    break

            if not target_entity:
                continue

            # Find target PK field
            pk_fields = [f for f in target_entity.fields if f.primary_key]
            target_has_pk = bool(pk_fields)
            target_pk = pk_fields[0] if pk_fields else None

            # Type match
            types_match = (
                target_pk is not None and field.data_type == target_pk.data_type
            )

            confidence = _inferred_confidence(
                name_match=True,
                types_match=types_match,
                target_has_pk=target_has_pk,
            )

            if confidence < 0.50:
                continue

            evidence = [
                f"Column name '{field.name}' matches the pattern for a reference to '{target_entity.name}'.",
            ]
            if types_match and target_pk:
                evidence.append(
                    f"Data types are compatible: '{field.data_type}' ↔ '{target_pk.data_type}'."
                )
            if target_has_pk:
                evidence.append(f"'{target_entity.name}' has a primary key.")
            evidence.append("No foreign key constraint is declared.")

            findings.append(Finding(
                rule_id="SQL-003",
                database_type=database_type,
                entity=entity.name,
                field=field.name,
                severity="medium",
                confidence=confidence,
                title="Possible undeclared relationship",
                description=(
                    f"'{entity.name}.{field.name}' appears to reference "
                    f"'{target_entity.name}' but no foreign key constraint is declared."
                ),
                evidence=evidence,
                impact=(
                    "Orphaned values may be introduced because referential integrity "
                    "is not enforced by the database."
                ),
                recommendation=(
                    "Review unmatched values and application behavior. "
                    "Consider adding a foreign key constraint after validation and backup."
                ),
                suggested_command=(
                    f"ALTER TABLE {entity.name}\n"
                    f"ADD CONSTRAINT fk_{entity.name}_{field.name}\n"
                    f"FOREIGN KEY ({field.name})\n"
                    f"REFERENCES {target_entity.name}(id);"
                ),
            ))

    return findings


# ---------------------------------------------------------------------------
# SQL-004 — Inconsistent naming convention
# ---------------------------------------------------------------------------

def rule_sql_004(
    entities: Sequence[EntityInfo],
    relationships: Sequence[RelationshipInfo],
    database_type: str = "sqlite",
) -> list[Finding]:
    """Fire when snake_case and camelCase field names coexist in the schema."""
    snake_examples: list[str] = []
    camel_examples: list[str] = []

    for entity in _tables(entities):
        for field in entity.fields:
            conv = _detect_convention(field.name)
            label = f"{entity.name}.{field.name}"
            if conv == "snake" and "_" in field.name:  # only multi-word snake
                snake_examples.append(label)
            elif conv == "camel":
                camel_examples.append(label)

    if not (snake_examples and camel_examples):
        return []

    snake_sample = snake_examples[:3]
    camel_sample = camel_examples[:3]

    return [Finding(
        rule_id="SQL-004",
        database_type=database_type,
        entity="(schema-wide)",
        severity="low",
        title="Inconsistent naming convention",
        description=(
            "The schema mixes snake_case and camelCase field names. "
            "This can cause confusion and errors in ORM mappings and query generation."
        ),
        evidence=[
            f"snake_case examples: {', '.join(snake_sample)}.",
            f"camelCase examples: {', '.join(camel_sample)}.",
        ],
        impact=(
            "Inconsistent naming leads to confusion in application code and "
            "makes automated query generation error-prone."
        ),
        recommendation=(
            "Choose one naming convention for future schema changes. "
            "Do not rename production fields automatically — plan a migration carefully."
        ),
    )]


# ---------------------------------------------------------------------------
# SQL-005 — Suspicious string data type
# ---------------------------------------------------------------------------

def rule_sql_005(
    entities: Sequence[EntityInfo],
    relationships: Sequence[RelationshipInfo],
    database_type: str = "sqlite",
) -> list[Finding]:
    """Fire when a column name implies date/numeric/boolean but the type is text."""
    findings: list[Finding] = []

    for entity in _tables(entities):
        for field in entity.fields:
            if field.data_type != "text":
                continue

            if _DATE_NAME_RE.search(field.name):
                kind, sev = "date or timestamp", "medium"
            elif _BOOL_NAME_RE.search(field.name):
                kind, sev = "boolean flag", "medium"
            elif _NUMERIC_NAME_RE.search(field.name):
                kind, sev = "numeric value", "low"
            else:
                continue

            findings.append(Finding(
                rule_id="SQL-005",
                database_type=database_type,
                entity=entity.name,
                field=field.name,
                severity=sev,
                title="Suspicious string data type",
                description=(
                    f"'{entity.name}.{field.name}' stores a {kind} "
                    f"but its data type is text ('{field.data_type}')."
                ),
                evidence=[
                    f"Column name '{field.name}' suggests a {kind}.",
                    f"Declared data type: '{field.data_type}'.",
                    "Storing typed data as text prevents native comparison, sorting, and validation.",
                ],
                impact=(
                    "Text storage for typed values prevents range queries, sorting, "
                    "and database-level validation. It can lead to silent data corruption."
                ),
                recommendation=(
                    "Validate existing values and application behavior. "
                    "Consider migrating to a native type in a controlled migration with backup."
                ),
            ))

    return findings


# ---------------------------------------------------------------------------
# SQL-006 — Excessive nullable columns
# ---------------------------------------------------------------------------

def rule_sql_006(
    entities: Sequence[EntityInfo],
    relationships: Sequence[RelationshipInfo],
    database_type: str = "sqlite",
) -> list[Finding]:
    """Fire when more than 70% of a table's columns are nullable."""
    findings: list[Finding] = []
    _THRESHOLD = 0.70
    _MIN_COLUMNS = 5

    for entity in _tables(entities):
        cols = entity.fields
        if len(cols) < _MIN_COLUMNS:
            continue

        nullable_count = sum(1 for f in cols if f.nullable and not f.primary_key)
        total = len(cols)
        ratio = nullable_count / total

        if ratio <= _THRESHOLD:
            continue

        nullable_names = [f.name for f in cols if f.nullable and not f.primary_key]
        findings.append(Finding(
            rule_id="SQL-006",
            database_type=database_type,
            entity=entity.name,
            severity="low",
            title="Excessive nullable columns",
            description=(
                f"Table '{entity.name}' has {nullable_count}/{total} nullable columns "
                f"({ratio:.0%}), which exceeds the 70% threshold."
            ),
            evidence=[
                f"Nullable columns ({nullable_count}/{total}): {', '.join(nullable_names[:8])}{'…' if len(nullable_names) > 8 else ''}.",
                f"Nullable ratio: {ratio:.1%}.",
            ],
            impact=(
                "High nullable ratio may indicate the table combines multiple entity shapes "
                "or optional subtypes, making queries and constraints harder to reason about."
            ),
            recommendation=(
                "Review whether the table stores several conceptually distinct entity types. "
                "Consider splitting into separate tables or using explicit subtype columns."
            ),
        ))

    return findings


# ---------------------------------------------------------------------------
# Inferred relationship builder (shared by SQL-003 and run_all_sql_rules)
# ---------------------------------------------------------------------------

def _build_inferred_relationships(
    entities: Sequence[EntityInfo],
    existing_relationships: Sequence[RelationshipInfo],
) -> list[RelationshipInfo]:
    """Return RelationshipInfo for _id columns that look like undeclared FKs.

    Only emits relationships with confidence >= 0.50. Skips columns that
    already have a declared FK constraint.
    """
    table_map: dict[str, EntityInfo] = {e.name.lower(): e for e in _tables(entities)}
    declared_pairs = {
        (r.source_entity.lower(), r.source_field.lower())
        for r in existing_relationships
        if r.declared
    }

    inferred: list[RelationshipInfo] = []

    for entity in _tables(entities):
        for field in entity.fields:
            if field.foreign_key_target:
                continue
            if (entity.name.lower(), field.name.lower()) in declared_pairs:
                continue

            candidates = _candidate_table_names(field.name)
            if not candidates:
                continue

            target_entity: EntityInfo | None = None
            for cand in candidates:
                if cand in table_map and cand != entity.name.lower():
                    target_entity = table_map[cand]
                    break

            if not target_entity:
                continue

            pk_fields = [f for f in target_entity.fields if f.primary_key]
            target_pk = pk_fields[0] if pk_fields else None
            types_match = target_pk is not None and field.data_type == target_pk.data_type

            confidence = _inferred_confidence(
                name_match=True,
                types_match=types_match,
                target_has_pk=bool(pk_fields),
            )
            if confidence < 0.50:
                continue

            inferred.append(RelationshipInfo(
                source_entity=entity.name,
                source_field=field.name,
                target_entity=target_entity.name,
                target_field=target_pk.name if target_pk else "id",
                declared=False,
                confidence=confidence,
                evidence=["inferred from column naming convention"],
            ))

    return inferred


# ---------------------------------------------------------------------------
# Run all rules
# ---------------------------------------------------------------------------

def run_all_sql_rules(result: AnalysisResult) -> list[Finding]:
    """Apply all six SQL rules to *result* and return the combined findings list.

    Also injects inferred relationships (from naming-convention analysis) into
    result.relationships so the ER diagram can draw dashed lines for them.
    """
    db_type = result.source_type
    entities = result.entities
    relationships = result.relationships

    all_findings: list[Finding] = []
    for rule_fn in (
        rule_sql_001,
        rule_sql_002,
        rule_sql_003,
        rule_sql_004,
        rule_sql_005,
        rule_sql_006,
    ):
        all_findings.extend(rule_fn(entities, relationships, db_type))

    result.findings = all_findings

    # Add inferred relationships so the ER diagram draws dashed connection lines.
    # Only add pairs not already present as declared FKs.
    existing_pairs = {(r.source_entity, r.source_field) for r in result.relationships}
    for rel in _build_inferred_relationships(entities, relationships):
        if (rel.source_entity, rel.source_field) not in existing_pairs:
            result.relationships.append(rel)

    return all_findings
