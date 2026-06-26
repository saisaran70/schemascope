"""JSON analysis exporter (PRD §27.2).

Output shape
------------
{
  "analysis_metadata": { source_type, source_name, analysed_at, ... },
  "entities": [ { name, entity_type, fields: [...], indexes: [...] } ],
  "relationships": [ { source_entity, source_field, target_entity, ... } ],
  "findings": [ { rule_id, severity, entity, ... } ],
  "warnings": [ "..." ]
}

Security: raw sampled values and credentials must never appear in output.
"""
from __future__ import annotations

import dataclasses
import json
from typing import Any

from models.schema_models import AnalysisResult, EntityInfo, FieldInfo, Finding, RelationshipInfo

# Fields that must never be serialised (credentials, raw data)
_BLOCKED_KEYS: frozenset[str] = frozenset({"password", "raw_values", "sample_data"})


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def export_json(result: AnalysisResult, indent: int = 2) -> str:
    """Return the analysis as a pretty-printed JSON string."""
    payload = _build_payload(result)
    return json.dumps(payload, indent=indent, default=str, ensure_ascii=False)


def export_json_dict(result: AnalysisResult) -> dict[str, Any]:
    """Return the analysis as a plain dict (useful for Streamlit or further processing)."""
    return _build_payload(result)


# ---------------------------------------------------------------------------
# Payload builder
# ---------------------------------------------------------------------------

def _build_payload(result: AnalysisResult) -> dict[str, Any]:
    return {
        "analysis_metadata": _metadata(result),
        "entities": [_serialise_entity(e) for e in result.entities],
        "relationships": [_serialise_relationship(r) for r in result.relationships],
        "findings": [_serialise_finding(f) for f in result.findings],
        "warnings": list(result.warnings),
    }


def _metadata(result: AnalysisResult) -> dict[str, Any]:
    meta: dict[str, Any] = {
        "source_type": result.source_type,
        "source_name": result.source_name,
        "analysed_at": result.analysed_at,
        "entity_count": len(result.entities),
        "relationship_count": len(result.relationships),
        "finding_count": len(result.findings),
        "warning_count": len(result.warnings),
        "generator": "SchemaScope v1",
        "note": (
            "This report is read-only. "
            "Suggested commands require manual review and a backup before execution."
        ),
    }
    # Merge extra metadata from result, excluding blocked keys
    for k, v in (result.metadata or {}).items():
        if k not in _BLOCKED_KEYS:
            meta[k] = v
    return meta


def _serialise_entity(e: EntityInfo) -> dict[str, Any]:
    return {
        "name": e.name,
        "entity_type": e.entity_type,
        "fields": [_serialise_field(f) for f in e.fields],
        "indexes": e.indexes,
        "row_count": e.row_count,
        "metadata": {k: v for k, v in (e.metadata or {}).items() if k not in _BLOCKED_KEYS},
    }


def _serialise_field(f: FieldInfo) -> dict[str, Any]:
    return {
        "name": f.name,
        "data_type": f.data_type,
        "nullable": f.nullable,
        "primary_key": f.primary_key,
        "unique": f.unique,
        "default_value": f.default_value,
        "foreign_key_target": f.foreign_key_target,
        "indexed": f.indexed,
        "index_names": f.index_names,
    }


def _serialise_relationship(r: RelationshipInfo) -> dict[str, Any]:
    return {
        "source_entity": r.source_entity,
        "source_field": r.source_field,
        "target_entity": r.target_entity,
        "target_field": r.target_field,
        "declared": r.declared,
        "confidence": r.confidence,
        "evidence": r.evidence,
        "relationship_type": r.relationship_type,
    }


def _serialise_finding(f: Finding) -> dict[str, Any]:
    return {
        "rule_id": f.rule_id,
        "database_type": f.database_type,
        "entity": f.entity,
        "field": f.field,
        "severity": f.severity,
        "confidence": f.confidence,
        "title": f.title,
        "description": f.description,
        "evidence": f.evidence,
        "impact": f.impact,
        "recommendation": f.recommendation,
        "suggested_command": f.suggested_command,
        "review_status": f.review_status,
    }
