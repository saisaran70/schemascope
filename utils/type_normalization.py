"""Normalize raw SQL type strings to canonical short names.

Canonical output values: integer, real, text, blob, numeric, boolean,
datetime, date, time, json, unknown.
"""
from __future__ import annotations

import re

# Map of normalized base-type → canonical name.
# Keys are checked after stripping length/precision suffixes and uppercasing.
_TYPE_MAP: dict[str, str] = {
    # Integer family
    "INT": "integer",
    "INTEGER": "integer",
    "TINYINT": "integer",
    "SMALLINT": "integer",
    "MEDIUMINT": "integer",
    "BIGINT": "integer",
    "INT2": "integer",
    "INT4": "integer",
    "INT8": "integer",
    "UNSIGNED BIG INT": "integer",
    "YEAR": "integer",
    # Real / float family
    "REAL": "real",
    "FLOAT": "real",
    "DOUBLE": "real",
    "DOUBLE PRECISION": "real",
    # Numeric / decimal family
    "NUMERIC": "numeric",
    "DECIMAL": "numeric",
    "NUMBER": "numeric",
    # Text family
    "TEXT": "text",
    "TINYTEXT": "text",
    "MEDIUMTEXT": "text",
    "LONGTEXT": "text",
    "CLOB": "text",
    "CHARACTER": "text",
    "VARCHAR": "text",
    "NVARCHAR": "text",
    "NCHAR": "text",
    "CHAR": "text",
    "VARYING CHARACTER": "text",
    "NATIVE CHARACTER": "text",
    "STRING": "text",
    "ENUM": "text",
    "SET": "text",
    # Boolean
    "BOOLEAN": "boolean",
    "BOOL": "boolean",
    "BIT": "boolean",
    # Blob / binary
    "BLOB": "blob",
    "TINYBLOB": "blob",
    "MEDIUMBLOB": "blob",
    "LONGBLOB": "blob",
    "BINARY": "blob",
    "VARBINARY": "blob",
    # Temporal
    "DATETIME": "datetime",
    "TIMESTAMP": "datetime",
    "DATE": "date",
    "TIME": "time",
    # JSON
    "JSON": "json",
    "JSONB": "json",
}

# Regex to strip length/precision suffixes, e.g. VARCHAR(255) → VARCHAR
_SUFFIX_RE = re.compile(r"\s*\(.*\)\s*$")


def normalize_sql_type(raw: str) -> str:
    """Return a canonical type name for *raw*.

    Examples
    --------
    normalize_sql_type("VARCHAR(255)")  -> "text"
    normalize_sql_type("INT")           -> "integer"
    normalize_sql_type("DECIMAL(10,2)") -> "numeric"
    normalize_sql_type("")              -> "unknown"
    """
    if not raw or not raw.strip():
        return "unknown"

    # Strip SQLAlchemy's NullType representation
    stripped = raw.strip()
    if stripped.upper() in ("NULL", "NULLTYPE"):
        return "unknown"

    cleaned = _SUFFIX_RE.sub("", stripped).upper()

    # Direct lookup
    if cleaned in _TYPE_MAP:
        return _TYPE_MAP[cleaned]

    # Prefix-based fallback for compound types not in the map
    for key, canonical in _TYPE_MAP.items():
        if cleaned.startswith(key):
            return canonical

    # Return the cleaned type name itself rather than a generic "unknown"
    # so the diagram shows e.g. "geometry" instead of "unknown"
    return cleaned.lower() if cleaned else "unknown"


def is_likely_date_type(raw: str) -> bool:
    """Return True when the normalized type is date, time, or datetime."""
    return normalize_sql_type(raw) in ("date", "time", "datetime")


def is_likely_numeric_type(raw: str) -> bool:
    """Return True when the normalized type is numeric or integer or real."""
    return normalize_sql_type(raw) in ("integer", "real", "numeric")


def is_text_type(raw: str) -> bool:
    """Return True when the normalized type is text."""
    return normalize_sql_type(raw) == "text"
