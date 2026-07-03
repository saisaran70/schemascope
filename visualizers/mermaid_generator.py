"""Mermaid diagram generator (PRD §13).

SQL databases  → erDiagram  (declared FKs as solid lines, inferred as dashed)
Diagram limits → 50 entities max before requesting a filter
"""
from __future__ import annotations

import re
from typing import Sequence

from models.schema_models import AnalysisResult, EntityInfo, FieldInfo, RelationshipInfo

_MAX_ENTITIES = 50

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_er_diagram(
    result: AnalysisResult,
    selected_entities: list[str] | None = None,
    max_entities: int = _MAX_ENTITIES,
) -> str:
    """Return a Mermaid ``erDiagram`` source string.

    Parameters
    ----------
    result:            The AnalysisResult to visualize.
    selected_entities: When provided, only render these entity names.
    max_entities:      Entities-per-diagram cap (default 50).

    Returns a valid Mermaid string, or a ``%%`` comment block explaining
    why the diagram was not generated (too many entities, empty schema).
    """
    entities = _filter_entities(result.entities, selected_entities)

    if not entities:
        return "erDiagram\n%% No entities to display."

    if len(entities) > max_entities and selected_entities is None:
        return (
            f"erDiagram\n"
            f"%% Schema has {len(result.entities)} entities — "
            f"above the {max_entities}-entity display limit.\n"
            f"%% Use the entity filter to select a subset and regenerate."
        )

    entity_names_safe = _build_safe_name_map(entities)
    lines: list[str] = ["erDiagram"]

    # --- Entity blocks ---
    for entity in entities:
        safe = entity_names_safe[entity.name]
        lines.append(f"    {safe} {{")
        for field in entity.fields:
            lines.append("        " + _format_field(field))
        lines.append("    }")

    # --- Relationship lines ---
    included_names = {e.name for e in entities}

    # Track (source_entity, target_entity) pairs already drawn to avoid duplicates.
    drawn: set[tuple[str, str]] = set()

    # 1. Declared + inferred relationships from result.relationships (populated
    #    by the analyzer and the rules engine).
    for rel in result.relationships:
        if rel.source_entity not in included_names:
            continue
        if rel.target_entity not in included_names:
            continue

        src = entity_names_safe.get(rel.source_entity, _escape(rel.source_entity))
        tgt = entity_names_safe.get(rel.target_entity, _escape(rel.target_entity))
        connector = "||--o{" if rel.declared else "||..o{"
        label = rel.source_field if rel.declared else f"{rel.source_field} ({int(rel.confidence * 100)}%)"
        lines.append(f'    {src} {connector} {tgt} : "{label}"')
        drawn.add((rel.source_entity, rel.target_entity))

    # 2. Fallback: extract declared FKs directly from field.foreign_key_target.
    #    Handles sessions analysed before result.relationships was populated, and
    #    databases whose FK constraints are stored in field metadata but were not
    #    yet reflected in result.relationships.
    for entity in entities:
        for field in entity.fields:
            if not field.foreign_key_target:
                continue
            # foreign_key_target format: "referred_table.referred_column"
            target_table = field.foreign_key_target.split(".")[0]
            if target_table not in included_names:
                continue
            if (entity.name, target_table) in drawn:
                continue
            src = entity_names_safe.get(entity.name, _escape(entity.name))
            tgt = entity_names_safe.get(target_table, _escape(target_table))
            connector = "||--o{"
            lines.append(f'    {src} {connector} {tgt} : "{field.name}"')
            drawn.add((entity.name, target_table))

    # 3. Fallback: infer FK connections by naming convention (_id / Id columns).
    #    Handles both plain table names ("patients") and module-prefixed names
    #    ("patient_patients") by matching the last underscore-separated word.
    entity_map = {e.name.lower(): e for e in entities}

    # last_word_index: last word of each table name → list of matching entities.
    # e.g. "patient_patients" → last word "patients" → [patient_patients entity]
    last_word_index: dict[str, list[EntityInfo]] = {}
    for e in entities:
        last_word = e.name.lower().split("_")[-1]
        last_word_index.setdefault(last_word, []).append(e)

    _id_re = re.compile(r"^(.+)_id$", re.IGNORECASE)
    _camel_id_re = re.compile(r"^(.+)Id$")

    for entity in entities:
        for field in entity.fields:
            if field.foreign_key_target:
                continue  # already handled above
            m = _id_re.match(field.name) or _camel_id_re.match(field.name)
            if not m:
                continue
            base = m.group(1).lower()
            target_entity: EntityInfo | None = None

            for cand in (base, base + "s", base + "es"):
                # Direct table name match (e.g. "patients" table)
                if cand in entity_map and cand != entity.name.lower():
                    target_entity = entity_map[cand]
                    break
                # Module-prefixed match: table whose last word is the candidate
                # e.g. patient_id → cand "patients" → "patient_patients" ✓
                by_last = [
                    e for e in last_word_index.get(cand, [])
                    if e.name.lower() != entity.name.lower()
                ]
                if len(by_last) == 1:  # only infer when unambiguous
                    target_entity = by_last[0]
                    break

            if not target_entity:
                continue
            if (entity.name, target_entity.name) in drawn:
                continue
            src = entity_names_safe.get(entity.name, _escape(entity.name))
            tgt = entity_names_safe.get(target_entity.name, _escape(target_entity.name))
            connector = "||..o{"
            lines.append(f'    {src} {connector} {tgt} : "{field.name}"')
            drawn.add((entity.name, target_entity.name))

    return "\n".join(lines)


def diagram_warnings(
    result: AnalysisResult,
    selected_entities: list[str] | None = None,
    max_entities: int = _MAX_ENTITIES,
) -> list[str]:
    """Return display warnings for the diagram (large schema, missing endpoints, etc.)."""
    warnings: list[str] = []
    entities = _filter_entities(result.entities, selected_entities)

    if len(result.entities) > max_entities and selected_entities is None:
        warnings.append(
            f"Schema has {len(result.entities)} entities. "
            f"Select up to {max_entities} entities to display the diagram."
        )

    # Relationships whose endpoints were filtered out
    included = {e.name for e in entities}
    hidden_rels = [
        r for r in result.relationships
        if r.source_entity not in included or r.target_entity not in included
    ]
    if hidden_rels and selected_entities:
        warnings.append(
            f"{len(hidden_rels)} relationship(s) not shown because one or both "
            "endpoints are outside the selected entity set."
        )

    return warnings


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _filter_entities(
    entities: Sequence[EntityInfo],
    selected: list[str] | None,
) -> list[EntityInfo]:
    if selected is None:
        return list(entities)
    sel_set = set(selected)
    return [e for e in entities if e.name in sel_set]


def _escape(name: str) -> str:
    """Replace characters that break Mermaid entity names with underscores."""
    return re.sub(r"[^a-zA-Z0-9_]", "_", name)


def _build_safe_name_map(entities: Sequence[EntityInfo]) -> dict[str, str]:
    """Return {original_name: safe_mermaid_name}, resolving collisions with a suffix."""
    seen: dict[str, int] = {}
    result: dict[str, str] = {}
    for entity in entities:
        base = _escape(entity.name)
        if base in seen:
            seen[base] += 1
            safe = f"{base}_{seen[base]}"
        else:
            seen[base] = 0
            safe = base
        result[entity.name] = safe
    return result


def _format_field(field: FieldInfo) -> str:
    """Return one erDiagram column line: ``type name [PK|FK]``."""
    # Mermaid type must be a single token — replace spaces in type names
    dtype = field.data_type.replace(" ", "_") if field.data_type else "unknown"
    name = _escape(field.name)

    if field.primary_key and field.foreign_key_target:
        marker = "PK,FK"
    elif field.primary_key:
        marker = "PK"
    elif field.foreign_key_target:
        marker = "FK"
    else:
        marker = ""

    return f"{dtype} {name}{' ' + marker if marker else ''}"
