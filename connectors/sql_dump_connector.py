"""Parse a MySQL dump (.sql) file and build an AnalysisResult.

No live database connection required — reads CREATE TABLE DDL directly.
Supports the med360.sql format: backtick-quoted names, no explicit FK constraints,
AUTO_INCREMENT marks the primary key.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone

from models.schema_models import AnalysisResult, EntityInfo, FieldInfo

# Match each CREATE TABLE `name` (...) ENGINE=... block
_TABLE_BLOCK_RE = re.compile(
    r'CREATE\s+TABLE\s+`(\w+)`\s*\((.*?)\)\s*ENGINE',
    re.DOTALL | re.IGNORECASE,
)

# Match a column definition line: starts with a backtick-quoted identifier
_COL_RE = re.compile(r'^\s*`(\w+)`\s+(.+)$', re.IGNORECASE)


def _extract_mysql_type(rest: str) -> str:
    """Return the MySQL base type name in lowercase for display in the ER diagram.

    Examples:
        "VARCHAR(255) NULL"      → "varchar"
        "INT UNSIGNED AUTO_INC"  → "int"
        "TINYINT(1) NULL"        → "tinyint"
        "DECIMAL(10,2) NULL"     → "decimal"
        "ENUM('A','B') NULL"     → "enum"
        "DATETIME NULL"          → "datetime"
        "JSON NULL"              → "json"
    """
    # Strip everything from '(' onward to get the bare type name
    base = rest.split('(')[0].strip().split()[0]
    return base.lower() if base else 'unknown'


def parse_sql_dump(content: str, source_name: str = "dump.sql") -> AnalysisResult:
    """Parse all CREATE TABLE blocks from a MySQL dump and return an AnalysisResult.

    FKs are not declared in med360.sql, so foreign_key_target is left None;
    the mermaid_generator infers relationships from _id column naming conventions.
    """
    entities: list[EntityInfo] = []
    warnings: list[str] = []

    for m in _TABLE_BLOCK_RE.finditer(content):
        table_name = m.group(1)
        body = m.group(2)
        fields: list[FieldInfo] = []

        for line in body.splitlines():
            line = line.strip().rstrip(',')
            if not line or not line.startswith('`'):
                continue  # skip KEY / CONSTRAINT / blank lines

            col_m = _COL_RE.match(line)
            if not col_m:
                continue

            col_name = col_m.group(1)
            rest = col_m.group(2).strip()
            rest_upper = rest.upper()

            is_pk = 'AUTO_INCREMENT' in rest_upper or col_name == '_id'
            nullable = 'NOT NULL' not in rest_upper

            fields.append(FieldInfo(
                name=col_name,
                data_type=_extract_mysql_type(rest),
                nullable=nullable,
                primary_key=is_pk,
                unique=is_pk,
                default_value=None,
                foreign_key_target=None,
                indexed=is_pk,
                index_names=[],
            ))

        if not fields:
            warnings.append(f"No columns parsed for table '{table_name}'.")
            continue

        entities.append(EntityInfo(
            name=table_name,
            entity_type='table',
            fields=fields,
            indexes=[],
            metadata={'source': 'sql_dump'},
        ))

    if not entities:
        warnings.append("No CREATE TABLE statements found in the uploaded file.")

    return AnalysisResult(
        source_type='sqldump',
        source_name=source_name,
        analysed_at=datetime.now(timezone.utc).isoformat(),
        entities=entities,
        relationships=[],
        findings=[],
        warnings=warnings,
    )
