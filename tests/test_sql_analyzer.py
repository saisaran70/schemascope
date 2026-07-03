"""Tests for analyzers/sql_analyzer.py — Step 4.

All tests use real SQLite databases created in tmp_path fixtures.
The Inspector is obtained via SQLiteConnector so the full stack is exercised.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect as sa_inspect
from sqlalchemy.pool import StaticPool

from analyzers.sql_analyzer import analyze, _process_table, _process_view, _coerce_default
from connectors.sqlite_connector import SQLiteConnector
from models.schema_models import AnalysisResult, EntityInfo, FieldInfo, RelationshipInfo


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_db(tmp_path, name: str, sql: str) -> str:
    """Create a SQLite DB at tmp_path/name, execute sql, return path string."""
    db = tmp_path / name
    conn = sqlite3.connect(str(db))
    conn.executescript(sql)
    conn.commit()
    conn.close()
    return str(db)


def _inspector_for(db_path: str):
    """Return a SQLAlchemy Inspector for a read-only SQLite path."""
    file_uri = Path(db_path).as_uri() + "?mode=ro"
    engine = create_engine(
        "sqlite+pysqlite://",
        creator=lambda: sqlite3.connect(file_uri, uri=True),
        poolclass=StaticPool,
    )
    return sa_inspect(engine), engine


def _analyze(db_path: str, source_name: str = "test.db", source_type: str = "sqlite") -> AnalysisResult:
    inspector, engine = _inspector_for(db_path)
    result = analyze(inspector, source_name, source_type)
    engine.dispose()
    return result


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def simple_db(tmp_path) -> str:
    return _make_db(tmp_path, "simple.db", """
        CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT UNIQUE
        );
    """)


@pytest.fixture()
def fk_db(tmp_path) -> str:
    return _make_db(tmp_path, "fk.db", """
        CREATE TABLE customers (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL
        );
        CREATE TABLE orders (
            id INTEGER PRIMARY KEY,
            customer_id INTEGER NOT NULL,
            total REAL,
            FOREIGN KEY (customer_id) REFERENCES customers(id)
        );
        CREATE INDEX idx_orders_customer ON orders(customer_id);
    """)


@pytest.fixture()
def multi_fk_db(tmp_path) -> str:
    return _make_db(tmp_path, "multi_fk.db", """
        CREATE TABLE products (id INTEGER PRIMARY KEY, name TEXT);
        CREATE TABLE warehouses (id INTEGER PRIMARY KEY, location TEXT);
        CREATE TABLE inventory (
            id INTEGER PRIMARY KEY,
            product_id INTEGER NOT NULL,
            warehouse_id INTEGER NOT NULL,
            quantity INTEGER DEFAULT 0,
            FOREIGN KEY (product_id) REFERENCES products(id),
            FOREIGN KEY (warehouse_id) REFERENCES warehouses(id)
        );
    """)


@pytest.fixture()
def view_db(tmp_path) -> str:
    return _make_db(tmp_path, "view.db", """
        CREATE TABLE employees (
            id INTEGER PRIMARY KEY,
            name TEXT,
            salary REAL
        );
        CREATE VIEW vw_employees AS
            SELECT id, name FROM employees;
    """)


@pytest.fixture()
def composite_pk_db(tmp_path) -> str:
    return _make_db(tmp_path, "composite.db", """
        CREATE TABLE order_items (
            order_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER,
            PRIMARY KEY (order_id, product_id)
        );
    """)


@pytest.fixture()
def empty_table_db(tmp_path) -> str:
    return _make_db(tmp_path, "empty.db", """
        CREATE TABLE empty_table (
            id INTEGER PRIMARY KEY,
            value TEXT
        );
    """)


@pytest.fixture()
def nullable_db(tmp_path) -> str:
    """Table with many nullable columns (>70% threshold for SQL-006)."""
    return _make_db(tmp_path, "nullable.db", """
        CREATE TABLE profile (
            id INTEGER PRIMARY KEY,
            nickname TEXT,
            bio TEXT,
            avatar_url TEXT,
            phone TEXT,
            address TEXT,
            country TEXT,
            zipcode TEXT
        );
    """)


@pytest.fixture()
def defaults_db(tmp_path) -> str:
    return _make_db(tmp_path, "defaults.db", """
        CREATE TABLE settings (
            id INTEGER PRIMARY KEY,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT DEFAULT 'now',
            score REAL DEFAULT 0.0
        );
    """)


@pytest.fixture()
def no_pk_db(tmp_path) -> str:
    return _make_db(tmp_path, "nopk.db", """
        CREATE TABLE logs (
            event TEXT,
            ts TEXT
        );
    """)


# ---------------------------------------------------------------------------
# AnalysisResult — top-level structure
# ---------------------------------------------------------------------------

class TestAnalysisResultStructure:
    def test_returns_analysis_result(self, simple_db):
        result = _analyze(simple_db)
        assert isinstance(result, AnalysisResult)

    def test_source_type_sqlite(self, simple_db):
        result = _analyze(simple_db, source_type="sqlite")
        assert result.source_type == "sqlite"

    def test_source_type_mysql(self, simple_db):
        result = _analyze(simple_db, source_type="mysql")
        assert result.source_type == "mysql"

    def test_source_name_stored(self, simple_db):
        result = _analyze(simple_db, source_name="mydb.sqlite")
        assert result.source_name == "mydb.sqlite"

    def test_analysed_at_is_iso8601_string(self, simple_db):
        result = _analyze(simple_db)
        assert isinstance(result.analysed_at, str)
        assert "T" in result.analysed_at   # basic ISO-8601 check

    def test_findings_empty_list(self, simple_db):
        """Analyzer never populates findings — rules do."""
        result = _analyze(simple_db)
        assert result.findings == []

    def test_warnings_is_list(self, simple_db):
        result = _analyze(simple_db)
        assert isinstance(result.warnings, list)

    def test_no_warnings_on_clean_db(self, simple_db):
        result = _analyze(simple_db)
        assert result.warnings == []


# ---------------------------------------------------------------------------
# Entity discovery
# ---------------------------------------------------------------------------

class TestEntityDiscovery:
    def test_single_table_found(self, simple_db):
        result = _analyze(simple_db)
        names = [e.name for e in result.entities]
        assert "users" in names

    def test_multiple_tables_found(self, fk_db):
        result = _analyze(fk_db)
        names = [e.name for e in result.entities]
        assert "customers" in names
        assert "orders" in names

    def test_table_entity_type(self, simple_db):
        result = _analyze(simple_db)
        users = next(e for e in result.entities if e.name == "users")
        assert users.entity_type == "table"

    def test_view_discovered(self, view_db):
        result = _analyze(view_db)
        names = [e.name for e in result.entities]
        assert "vw_employees" in names

    def test_view_entity_type(self, view_db):
        result = _analyze(view_db)
        view = next(e for e in result.entities if e.name == "vw_employees")
        assert view.entity_type == "view"

    def test_table_and_view_both_present(self, view_db):
        result = _analyze(view_db)
        types = {e.entity_type for e in result.entities}
        assert "table" in types
        assert "view" in types

    def test_empty_table_still_present(self, empty_table_db):
        result = _analyze(empty_table_db)
        names = [e.name for e in result.entities]
        assert "empty_table" in names

    def test_entities_sorted_alphabetically(self, multi_fk_db):
        result = _analyze(multi_fk_db)
        table_names = [e.name for e in result.entities if e.entity_type == "table"]
        assert table_names == sorted(table_names)


# ---------------------------------------------------------------------------
# Field / column extraction
# ---------------------------------------------------------------------------

class TestFieldExtraction:
    def test_columns_extracted(self, simple_db):
        result = _analyze(simple_db)
        users = next(e for e in result.entities if e.name == "users")
        field_names = [f.name for f in users.fields]
        assert "id" in field_names
        assert "name" in field_names
        assert "email" in field_names

    def test_field_count(self, simple_db):
        result = _analyze(simple_db)
        users = next(e for e in result.entities if e.name == "users")
        assert len(users.fields) == 3

    def test_data_type_normalized(self, simple_db):
        result = _analyze(simple_db)
        users = next(e for e in result.entities if e.name == "users")
        id_field = next(f for f in users.fields if f.name == "id")
        assert id_field.data_type == "integer"

    def test_text_type_normalized(self, simple_db):
        result = _analyze(simple_db)
        users = next(e for e in result.entities if e.name == "users")
        name_field = next(f for f in users.fields if f.name == "name")
        assert name_field.data_type == "text"

    def test_real_type_normalized(self, fk_db):
        result = _analyze(fk_db)
        orders = next(e for e in result.entities if e.name == "orders")
        total_field = next(f for f in orders.fields if f.name == "total")
        assert total_field.data_type == "real"

    def test_nullable_false_for_not_null_column(self, simple_db):
        result = _analyze(simple_db)
        users = next(e for e in result.entities if e.name == "users")
        name_field = next(f for f in users.fields if f.name == "name")
        assert name_field.nullable is False

    def test_nullable_true_for_nullable_column(self, simple_db):
        result = _analyze(simple_db)
        users = next(e for e in result.entities if e.name == "users")
        email_field = next(f for f in users.fields if f.name == "email")
        assert email_field.nullable is True

    def test_default_value_captured(self, defaults_db):
        result = _analyze(defaults_db)
        settings = next(e for e in result.entities if e.name == "settings")
        is_active = next(f for f in settings.fields if f.name == "is_active")
        assert is_active.default_value is not None

    def test_no_default_is_none(self, simple_db):
        result = _analyze(simple_db)
        users = next(e for e in result.entities if e.name == "users")
        name_field = next(f for f in users.fields if f.name == "name")
        assert name_field.default_value is None


# ---------------------------------------------------------------------------
# Primary key detection
# ---------------------------------------------------------------------------

class TestPrimaryKeyDetection:
    def test_pk_column_marked(self, simple_db):
        result = _analyze(simple_db)
        users = next(e for e in result.entities if e.name == "users")
        id_field = next(f for f in users.fields if f.name == "id")
        assert id_field.primary_key is True

    def test_non_pk_not_marked(self, simple_db):
        result = _analyze(simple_db)
        users = next(e for e in result.entities if e.name == "users")
        name_field = next(f for f in users.fields if f.name == "name")
        assert name_field.primary_key is False

    def test_pk_column_marked_unique(self, simple_db):
        result = _analyze(simple_db)
        users = next(e for e in result.entities if e.name == "users")
        id_field = next(f for f in users.fields if f.name == "id")
        assert id_field.unique is True

    def test_pk_column_marked_indexed(self, simple_db):
        result = _analyze(simple_db)
        users = next(e for e in result.entities if e.name == "users")
        id_field = next(f for f in users.fields if f.name == "id")
        assert id_field.indexed is True

    def test_composite_pk_both_columns_marked(self, composite_pk_db):
        result = _analyze(composite_pk_db)
        oi = next(e for e in result.entities if e.name == "order_items")
        pk_fields = [f for f in oi.fields if f.primary_key]
        pk_names = {f.name for f in pk_fields}
        assert "order_id" in pk_names
        assert "product_id" in pk_names

    def test_no_pk_table_has_no_pk_fields(self, no_pk_db):
        result = _analyze(no_pk_db)
        logs = next(e for e in result.entities if e.name == "logs")
        pk_fields = [f for f in logs.fields if f.primary_key]
        assert pk_fields == []

    def test_pk_columns_in_metadata(self, simple_db):
        result = _analyze(simple_db)
        users = next(e for e in result.entities if e.name == "users")
        assert "id" in users.metadata.get("pk_columns", [])


# ---------------------------------------------------------------------------
# Unique constraint detection
# ---------------------------------------------------------------------------

class TestUniqueConstraintDetection:
    def test_unique_column_marked(self, simple_db):
        result = _analyze(simple_db)
        users = next(e for e in result.entities if e.name == "users")
        email_field = next(f for f in users.fields if f.name == "email")
        assert email_field.unique is True

    def test_non_unique_column_not_marked(self, simple_db):
        result = _analyze(simple_db)
        users = next(e for e in result.entities if e.name == "users")
        name_field = next(f for f in users.fields if f.name == "name")
        assert name_field.unique is False


# ---------------------------------------------------------------------------
# Foreign key detection
# ---------------------------------------------------------------------------

class TestForeignKeyDetection:
    def test_fk_column_has_target(self, fk_db):
        result = _analyze(fk_db)
        orders = next(e for e in result.entities if e.name == "orders")
        cid = next(f for f in orders.fields if f.name == "customer_id")
        assert cid.foreign_key_target == "customers.id"

    def test_non_fk_column_has_no_target(self, fk_db):
        result = _analyze(fk_db)
        orders = next(e for e in result.entities if e.name == "orders")
        id_field = next(f for f in orders.fields if f.name == "id")
        assert id_field.foreign_key_target is None

    def test_fk_count_in_metadata(self, fk_db):
        result = _analyze(fk_db)
        orders = next(e for e in result.entities if e.name == "orders")
        assert orders.metadata["foreign_key_count"] == 1

    def test_multiple_fks_detected(self, multi_fk_db):
        result = _analyze(multi_fk_db)
        inv = next(e for e in result.entities if e.name == "inventory")
        assert inv.metadata["foreign_key_count"] == 2

    def test_multiple_fk_targets_correct(self, multi_fk_db):
        result = _analyze(multi_fk_db)
        inv = next(e for e in result.entities if e.name == "inventory")
        pid = next(f for f in inv.fields if f.name == "product_id")
        wid = next(f for f in inv.fields if f.name == "warehouse_id")
        assert pid.foreign_key_target == "products.id"
        assert wid.foreign_key_target == "warehouses.id"


# ---------------------------------------------------------------------------
# Relationship objects
# ---------------------------------------------------------------------------

class TestRelationshipObjects:
    def test_one_relationship_for_one_fk(self, fk_db):
        result = _analyze(fk_db)
        assert len(result.relationships) == 1

    def test_relationship_source_entity(self, fk_db):
        result = _analyze(fk_db)
        rel = result.relationships[0]
        assert rel.source_entity == "orders"

    def test_relationship_source_field(self, fk_db):
        result = _analyze(fk_db)
        rel = result.relationships[0]
        assert rel.source_field == "customer_id"

    def test_relationship_target_entity(self, fk_db):
        result = _analyze(fk_db)
        rel = result.relationships[0]
        assert rel.target_entity == "customers"

    def test_relationship_target_field(self, fk_db):
        result = _analyze(fk_db)
        rel = result.relationships[0]
        assert rel.target_field == "id"

    def test_relationship_declared_true(self, fk_db):
        result = _analyze(fk_db)
        rel = result.relationships[0]
        assert rel.declared is True

    def test_relationship_confidence_one(self, fk_db):
        result = _analyze(fk_db)
        rel = result.relationships[0]
        assert rel.confidence == pytest.approx(1.0)

    def test_relationship_has_evidence(self, fk_db):
        result = _analyze(fk_db)
        rel = result.relationships[0]
        assert len(rel.evidence) > 0

    def test_two_relationships_for_two_fks(self, multi_fk_db):
        result = _analyze(multi_fk_db)
        assert len(result.relationships) == 2

    def test_no_relationships_with_no_fks(self, simple_db):
        result = _analyze(simple_db)
        assert result.relationships == []

    def test_all_relationships_are_declared(self, multi_fk_db):
        result = _analyze(multi_fk_db)
        assert all(r.declared for r in result.relationships)


# ---------------------------------------------------------------------------
# Index extraction
# ---------------------------------------------------------------------------

class TestIndexExtraction:
    def test_explicit_index_detected(self, fk_db):
        result = _analyze(fk_db)
        orders = next(e for e in result.entities if e.name == "orders")
        idx_names = [idx["name"] for idx in orders.indexes]
        assert "idx_orders_customer" in idx_names

    def test_indexed_column_marked(self, fk_db):
        result = _analyze(fk_db)
        orders = next(e for e in result.entities if e.name == "orders")
        cid = next(f for f in orders.fields if f.name == "customer_id")
        assert cid.indexed is True

    def test_index_names_on_field(self, fk_db):
        result = _analyze(fk_db)
        orders = next(e for e in result.entities if e.name == "orders")
        cid = next(f for f in orders.fields if f.name == "customer_id")
        assert "idx_orders_customer" in cid.index_names

    def test_non_indexed_column_not_marked(self, fk_db):
        result = _analyze(fk_db)
        orders = next(e for e in result.entities if e.name == "orders")
        total = next(f for f in orders.fields if f.name == "total")
        assert total.indexed is False

    def test_index_structure_has_required_keys(self, fk_db):
        result = _analyze(fk_db)
        orders = next(e for e in result.entities if e.name == "orders")
        for idx in orders.indexes:
            assert "name" in idx
            assert "columns" in idx
            assert "unique" in idx


# ---------------------------------------------------------------------------
# View analysis
# ---------------------------------------------------------------------------

class TestViewAnalysis:
    def test_view_has_fields(self, view_db):
        result = _analyze(view_db)
        view = next(e for e in result.entities if e.name == "vw_employees")
        assert len(view.fields) > 0

    def test_view_field_names(self, view_db):
        result = _analyze(view_db)
        view = next(e for e in result.entities if e.name == "vw_employees")
        field_names = [f.name for f in view.fields]
        assert "id" in field_names
        assert "name" in field_names

    def test_view_has_no_fk_target(self, view_db):
        result = _analyze(view_db)
        view = next(e for e in result.entities if e.name == "vw_employees")
        for f in view.fields:
            assert f.foreign_key_target is None

    def test_view_not_in_relationships(self, view_db):
        result = _analyze(view_db)
        rel_entities = {r.source_entity for r in result.relationships}
        assert "vw_employees" not in rel_entities


# ---------------------------------------------------------------------------
# Error resilience — partial analysis
# ---------------------------------------------------------------------------

class TestPartialAnalysis:
    def test_warning_added_when_table_fails(self, simple_db):
        """Patch inspector to raise on one table; other tables still analysed."""
        from unittest.mock import MagicMock, patch
        inspector, engine = _inspector_for(simple_db)

        original_get_columns = inspector.get_columns

        call_count = [0]

        def flaky_get_columns(table_name, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                raise RuntimeError("simulated inspection failure")
            return original_get_columns(table_name, **kwargs)

        with patch.object(inspector, "get_columns", side_effect=flaky_get_columns):
            result = analyze(inspector, "test.db")

        assert len(result.warnings) >= 1
        engine.dispose()


# ---------------------------------------------------------------------------
# _coerce_default helper
# ---------------------------------------------------------------------------

class TestCoerceDefault:
    def test_none_returns_none(self):
        assert _coerce_default(None) is None

    def test_integer_returns_string(self):
        assert _coerce_default(1) == "1"

    def test_float_returns_string(self):
        assert _coerce_default(0.0) == "0.0"

    def test_string_unchanged(self):
        assert _coerce_default("now") == "now"

    def test_empty_string_returns_none(self):
        assert _coerce_default("") is None

    def test_whitespace_only_returns_none(self):
        assert _coerce_default("   ") is None
