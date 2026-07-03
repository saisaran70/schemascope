"""Quick debug script — shows what type strings SQLAlchemy returns for MySQL columns."""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from utils.type_normalization import normalize_sql_type

# Simulate what str(col["type"]) returns for common MySQL/SQLAlchemy types
test_cases = [
    # MySQL text variants
    "TEXT", "TINYTEXT", "MEDIUMTEXT", "LONGTEXT",
    # MySQL int variants
    "INT", "INT(11)", "TINYINT(1)", "BIGINT", "BIGINT(20)",
    # MySQL blob variants
    "BLOB", "LONGBLOB", "MEDIUMBLOB", "TINYBLOB",
    # Enum / set
    "ENUM('a','b','c')", "SET('x','y')",
    # Temporal
    "DATETIME", "DATE", "TIMESTAMP", "YEAR",
    # Float
    "FLOAT", "DOUBLE", "DECIMAL(10,2)",
    # Varchar
    "VARCHAR(255)", "VARCHAR(191)",
    # Boolean
    "BOOLEAN", "TINYINT(1)",
    # JSON
    "JSON",
    # SQLAlchemy NullType
    "NULL", "NULLTYPE",
    # Edge cases
    "", "   ", "GEOMETRY", "POINT",
]

print(f"{'Raw type':<35} {'Normalized'}")
print("-" * 55)
for t in test_cases:
    result = normalize_sql_type(t)
    marker = " ← UNKNOWN" if result == "unknown" else ""
    print(f"{t!r:<35} {result}{marker}")
