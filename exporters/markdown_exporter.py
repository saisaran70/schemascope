"""Markdown report exporter (PRD §27.1).

Structure
---------
# SchemaScope Analysis Report
## Analysis Summary
## Limitations and Warnings
## Entities
### <entity_name>
## Confirmed Relationships
## Inferred Relationships
## Recommendations
### High / Medium / Low
## Suggested Commands
## Analysis Metadata

Security: credentials and raw sampled values must never appear in output.
"""
from __future__ import annotations

import re
from typing import Sequence

_BLOCKED_KEYS: frozenset[str] = frozenset({"password", "raw_values", "sample_data"})

from models.schema_models import (
    AnalysisResult,
    EntityInfo,
    FieldInfo,
    Finding,
    RelationshipInfo,
)

_SEVERITY_ORDER = ("high", "medium", "low", "information")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def export_markdown(result: AnalysisResult) -> str:
    """Return the full Markdown report as a string."""
    sections: list[str] = [
        _section_header(result),
        _section_summary(result),
        _section_warnings(result),
        _section_entities(result.entities),
        _section_relationships(result.relationships),
        _section_recommendations(result.findings),
        _section_suggested_commands(result.findings),
        _section_metadata(result),
    ]
    return "\n\n".join(s for s in sections if s.strip())


def generate_export_filename(
    source_name: str,
    timestamp: str,
    file_suffix: str,
) -> str:
    """Return a safe export filename per PRD §27.4.

    e.g. generate_export_filename("mydb.sqlite", "20260626T140000", "report.md")
         → "schemascope_mydb_20260626T140000_report.md"
    """
    base = re.sub(r"[^a-zA-Z0-9_]", "_", source_name.rsplit(".", 1)[0])
    ts = re.sub(r"[^a-zA-Z0-9]", "", timestamp)[:15]
    return f"schemascope_{base}_{ts}_{file_suffix}"


# ---------------------------------------------------------------------------
# Sections
# ---------------------------------------------------------------------------

def _section_header(result: AnalysisResult) -> str:
    return (
        "# SchemaScope Analysis Report\n\n"
        f"> **Source:** {result.source_name}  \n"
        f"> **Type:** {result.source_type.upper()}  \n"
        f"> **Analysed:** {result.analysed_at}  \n"
        "> **Note:** This report is read-only. "
        "Suggested commands require manual review and a backup before execution."
    )


def _section_summary(result: AnalysisResult) -> str:
    tables = [e for e in result.entities if e.entity_type == "table"]
    views = [e for e in result.entities if e.entity_type == "view"]
    declared = [r for r in result.relationships if r.declared]
    inferred = [r for r in result.relationships if not r.declared]

    severity_counts = {s: 0 for s in _SEVERITY_ORDER}
    for f in result.findings:
        severity_counts[f.severity] = severity_counts.get(f.severity, 0) + 1

    lines = [
        "## Analysis Summary",
        "",
        f"| Item | Count |",
        f"|---|---|",
        f"| Tables | {len(tables)} |",
        f"| Views | {len(views)} |",
        f"| Total fields | {sum(len(e.fields) for e in result.entities)} |",
        f"| Confirmed relationships | {len(declared)} |",
        f"| Inferred relationships | {len(inferred)} |",
        f"| Findings — High | {severity_counts.get('high', 0)} |",
        f"| Findings — Medium | {severity_counts.get('medium', 0)} |",
        f"| Findings — Low | {severity_counts.get('low', 0)} |",
        f"| Findings — Information | {severity_counts.get('information', 0)} |",
    ]
    return "\n".join(lines)


def _section_warnings(result: AnalysisResult) -> str:
    if not result.warnings:
        return ""
    lines = ["## Limitations and Warnings", ""]
    for w in result.warnings:
        lines.append(f"- ⚠ {w}")
    return "\n".join(lines)


def _section_entities(entities: Sequence[EntityInfo]) -> str:
    if not entities:
        return "## Entities\n\n_No entities found._"

    parts = ["## Entities"]
    for entity in entities:
        parts.append(_entity_block(entity))
    return "\n\n".join(parts)


def _entity_block(entity: EntityInfo) -> str:
    kind = entity.entity_type.capitalize()
    lines = [f"### {entity.name} `({kind})`", ""]

    if not entity.fields:
        lines.append("_No columns._")
        return "\n".join(lines)

    # Field table
    lines += [
        "| Field | Type | Nullable | Default | PK | FK Target | Unique | Indexed |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for f in entity.fields:
        pk = "✓" if f.primary_key else ""
        unique = "✓" if f.unique else ""
        indexed = "✓" if f.indexed else ""
        nullable = "✓" if f.nullable else ""
        default = f.default_value or ""
        fk = f.foreign_key_target or ""
        lines.append(
            f"| `{f.name}` | {f.data_type} | {nullable} | {default} "
            f"| {pk} | {fk} | {unique} | {indexed} |"
        )

    if entity.indexes:
        lines += ["", "**Indexes**", ""]
        for idx in entity.indexes:
            cols = ", ".join(idx.get("columns", []))
            uniq = " (unique)" if idx.get("unique") else ""
            lines.append(f"- `{idx.get('name', '?')}` on ({cols}){uniq}")

    return "\n".join(lines)


def _section_relationships(relationships: Sequence[RelationshipInfo]) -> str:
    declared = [r for r in relationships if r.declared]
    inferred = [r for r in relationships if not r.declared]

    parts: list[str] = []

    parts.append("## Confirmed Relationships")
    if declared:
        parts.append("")
        parts.append("| Source | Field | Target | Field |")
        parts.append("|---|---|---|---|")
        for r in declared:
            parts.append(
                f"| `{r.source_entity}` | `{r.source_field}` "
                f"| `{r.target_entity}` | `{r.target_field}` |"
            )
    else:
        parts.append("\n_No confirmed relationships._")

    parts.append("")
    parts.append("## Inferred Relationships")
    if inferred:
        parts.append("")
        parts.append("| Source | Field | Target | Field | Confidence | Evidence |")
        parts.append("|---|---|---|---|---|---|")
        for r in inferred:
            conf = f"{int(r.confidence * 100)}%" if r.confidence is not None else "—"
            evidence_summary = "; ".join(r.evidence[:2]) if r.evidence else "—"
            parts.append(
                f"| `{r.source_entity}` | `{r.source_field}` "
                f"| `{r.target_entity}` | `{r.target_field}` "
                f"| {conf} | {evidence_summary} |"
            )
    else:
        parts.append("\n_No inferred relationships._")

    return "\n".join(parts)


def _section_recommendations(findings: Sequence[Finding]) -> str:
    if not findings:
        return "## Recommendations\n\n_No findings._"

    parts = ["## Recommendations"]

    for severity in _SEVERITY_ORDER:
        group = [f for f in findings if f.severity == severity]
        if not group:
            continue
        parts.append(f"\n### {severity.capitalize()}")
        for finding in group:
            parts.append(_finding_card(finding))

    return "\n".join(parts)


def _finding_card(f: Finding) -> str:
    lines = [
        "",
        f"#### {f.rule_id} — {f.title}",
        "",
        f"| Attribute | Value |",
        f"|---|---|",
        f"| Rule | `{f.rule_id}` |",
        f"| Entity | `{f.entity}`{' — field `' + f.field + '`' if f.field else ''} |",
        f"| Severity | **{f.severity.capitalize()}** |",
    ]
    if f.confidence is not None:
        lines.append(f"| Confidence | {int(f.confidence * 100)}% |")
    lines.append(f"| Status | {f.review_status.capitalize()} |")

    lines += [
        "",
        f"**Finding:** {f.description}",
        "",
        "**Evidence:**",
    ]
    for e in f.evidence:
        lines.append(f"- {e}")

    lines += [
        "",
        f"**Impact:** {f.impact}",
        "",
        f"**Recommendation:** {f.recommendation}",
    ]
    return "\n".join(lines)


def _section_suggested_commands(findings: Sequence[Finding]) -> str:
    with_commands = [f for f in findings if f.suggested_command]
    if not with_commands:
        return ""

    lines = [
        "## Suggested Commands",
        "",
        "> These commands are for **review only**. "
        "Never execute without validation and a backup.",
    ]
    for f in with_commands:
        lines += [
            "",
            f"### {f.rule_id} — `{f.entity}`{' / `' + f.field + '`' if f.field else ''}",
            "",
            "```sql",
            f.suggested_command.strip(),
            "```",
        ]
    return "\n".join(lines)


def _section_metadata(result: AnalysisResult) -> str:
    lines = [
        "## Analysis Metadata",
        "",
        f"| Key | Value |",
        f"|---|---|",
        f"| Source type | {result.source_type} |",
        f"| Source name | {result.source_name} |",
        f"| Analysed at | {result.analysed_at} |",
        f"| Total entities | {len(result.entities)} |",
        f"| Total relationships | {len(result.relationships)} |",
        f"| Total findings | {len(result.findings)} |",
    ]
    if result.metadata:
        for k, v in result.metadata.items():
            if k not in _BLOCKED_KEYS:
                lines.append(f"| {k} | {v} |")
    return "\n".join(lines)
