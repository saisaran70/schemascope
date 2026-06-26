"""SQL schema analyzer — converts a SQLAlchemy Inspector into an AnalysisResult.

Findings are NOT populated here; rules run separately (see rules/sql_rules.py).
Works identically for SQLite and MySQL because both expose the same Inspector API.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Inspector

from models.schema_models import (
    AnalysisResult,
    EntityInfo,
    FieldInfo,
    RelationshipInfo,
)
from utils.type_normalization import normalize_sql_type


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def analyze(
    inspector: Inspector,
    source_name: str,
    source_type: str = "sqlite",
) -> AnalysisResult:
    """Extract all schema metadata and return an AnalysisResult.

    Parameters
    ----------
    inspector:   SQLAlchemy Inspector bound to an open engine.
    source_name: Display label (file name or database name).
    source_type: "sqlite" | "mysql" — stored in the result.
    """
    entities: list[EntityInfo] = []
    relationships: list[RelationshipInfo] = []
    warnings: list[str] = []

    for table_name in sorted(inspector.get_table_names()):
        try:
            entity, rels = _process_table(inspector, table_name)
            entities.append(entity)
            relationships.extend(rels)
        except Exception as exc:
            warnings.append(f"Could not inspect table '{table_name}': {exc}")

    for view_name in sorted(inspector.get_view_names()):
        try:
            entity = _process_view(inspector, view_name)
            entities.append(entity)
        except Exception as exc:
            warnings.append(f"Could not inspect view '{view_name}': {exc}")

    return AnalysisResult(
        source_type=source_type,
        source_name=source_name,
        analysed_at=datetime.now(timezone.utc).isoformat(),
        entities=entities,
        relationships=relationships,
        findings=[],      # rules populate this separately
        warnings=warnings,
    )


# ---------------------------------------------------------------------------
# Table processing
# ---------------------------------------------------------------------------

def _process_table(
    inspector: Inspector,
    table_name: str,
) -> tuple[EntityInfo, list[RelationshipInfo]]:
    """Return (EntityInfo, [RelationshipInfo]) for one table."""

    columns = inspector.get_columns(table_name)
    pk_info = inspector.get_pk_constraint(table_name)
    fk_list = inspector.get_foreign_keys(table_name)
    unique_list = inspector.get_unique_constraints(table_name)
    index_list = inspector.get_indexes(table_name)

    pk_columns: set[str] = set(pk_info.get("constrained_columns", []))

    # column → "referred_table.referred_column" for single-col FKs
    fk_map: dict[str, str] = {}
    for fk in fk_list:
        for src, ref in zip(
            fk.get("constrained_columns", []),
            fk.get("referred_columns", []),
        ):
            fk_map[src] = f"{fk['referred_table']}.{ref}"

    # single-column unique constraints
    unique_single: set[str] = {
        uc["column_names"][0]
        for uc in unique_list
        if len(uc.get("column_names", [])) == 1
    }

    # column → list[index_name]
    indexed_map: dict[str, list[str]] = {}
    for idx in index_list:
        for col in idx.get("column_names") or []:
            indexed_map.setdefault(col, []).append(idx["name"])

    fields: list[FieldInfo] = []
    for col in columns:
        col_name: str = col["name"]
        is_pk = col_name in pk_columns
        fields.append(
            FieldInfo(
                name=col_name,
                data_type=normalize_sql_type(str(col.get("type", ""))),
                nullable=bool(col.get("nullable", True)),
                primary_key=is_pk,
                unique=is_pk or col_name in unique_single,
                default_value=_coerce_default(col.get("default")),
                foreign_key_target=fk_map.get(col_name),
                indexed=is_pk or col_name in indexed_map,
                index_names=indexed_map.get(col_name, []),
            )
        )

    entity = EntityInfo(
        name=table_name,
        entity_type="table",
        fields=fields,
        indexes=[
            {
                "name": idx.get("name", ""),
                "columns": idx.get("column_names", []),
                "unique": bool(idx.get("unique", False)),
            }
            for idx in index_list
        ],
        metadata={
            "pk_name": pk_info.get("name"),
            "pk_columns": list(pk_columns),
            "foreign_key_count": len(fk_list),
            "unique_constraint_count": len(unique_list),
        },
    )

    # One RelationshipInfo per FK column pair
    relationships: list[RelationshipInfo] = [
        RelationshipInfo(
            source_entity=table_name,
            source_field=src,
            target_entity=fk["referred_table"],
            target_field=ref,
            declared=True,
            confidence=1.0,
            evidence=["foreign key constraint declared in schema"],
        )
        for fk in fk_list
        for src, ref in zip(
            fk.get("constrained_columns", []),
            fk.get("referred_columns", []),
        )
    ]

    return entity, relationships


# ---------------------------------------------------------------------------
# View processing
# ---------------------------------------------------------------------------

def _process_view(inspector: Inspector, view_name: str) -> EntityInfo:
    """Return EntityInfo for a view (columns only — no FK/index metadata)."""
    try:
        columns = inspector.get_columns(view_name)
    except Exception as exc:
        return EntityInfo(
            name=view_name,
            entity_type="view",
            fields=[],
            metadata={"warning": f"Could not extract columns: {exc}"},
        )

    return EntityInfo(
        name=view_name,
        entity_type="view",
        fields=[
            FieldInfo(
                name=col["name"],
                data_type=normalize_sql_type(str(col.get("type", ""))),
                nullable=bool(col.get("nullable", True)),
            )
            for col in columns
        ],
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _coerce_default(value: Any) -> str | None:
    if value is None:
        return None
    s = str(value).strip()
    return s or None
