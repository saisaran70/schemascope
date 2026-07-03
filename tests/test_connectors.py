"""Tests for connectors/ — Step 3.

SQLite tests use real temp files.
MySQL tests mock the SQLAlchemy engine (no live server required).
"""
from __future__ import annotations

import os
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

from connectors.base import BaseConnector
from connectors.sqlite_connector import SQLiteConnector
from connectors.mysql_connector import MySQLConnector
from utils.errors import (
    AnalysisError,
    AuthenticationError,
    ConnectionError,
    InvalidFileError,
    PermissionError,
    SchemaError,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def good_sqlite_path(tmp_path) -> str:
    """A valid, readable SQLite database file."""
    db = tmp_path / "good.db"
    conn = sqlite3.connect(str(db))
    conn.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT)")
    conn.execute("INSERT INTO users VALUES (1, 'Alice')")
    conn.commit()
    conn.close()
    return str(db)


@pytest.fixture()
def good_sqlite_bytes(good_sqlite_path) -> bytes:
    """Raw bytes of the good SQLite database."""
    with open(good_sqlite_path, "rb") as f:
        return f.read()


@pytest.fixture()
def empty_sqlite_path(tmp_path) -> str:
    """A valid SQLite database with no tables."""
    db = tmp_path / "empty.db"
    conn = sqlite3.connect(str(db))
    conn.close()
    return str(db)


@pytest.fixture()
def multi_table_sqlite_path(tmp_path) -> str:
    """SQLite database with multiple tables and a foreign key."""
    db = tmp_path / "multi.db"
    conn = sqlite3.connect(str(db))
    conn.executescript("""
        CREATE TABLE customers (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT UNIQUE
        );
        CREATE TABLE orders (
            id INTEGER PRIMARY KEY,
            customer_id INTEGER NOT NULL,
            total REAL,
            FOREIGN KEY (customer_id) REFERENCES customers(id)
        );
        CREATE INDEX idx_orders_customer ON orders(customer_id);
    """)
    conn.commit()
    conn.close()
    return str(db)


# ---------------------------------------------------------------------------
# BaseConnector
# ---------------------------------------------------------------------------

class TestBaseConnector:
    def test_base_connector_is_abstract(self):
        """Cannot instantiate BaseConnector directly."""
        with pytest.raises(TypeError):
            BaseConnector()

    def test_concrete_subclass_must_implement_all_methods(self):
        """A subclass missing any abstract method cannot be instantiated."""
        class Incomplete(BaseConnector):
            def test_connection(self): pass
            # Missing get_inspector, get_engine, close

        with pytest.raises(TypeError):
            Incomplete()

    def test_context_manager_calls_close(self, good_sqlite_path):
        conn = SQLiteConnector(good_sqlite_path, "good.db")
        conn.test_connection()
        with conn:
            pass
        # After __exit__, engine should be disposed (None)
        assert conn._engine is None

    def test_context_manager_calls_close_on_exception(self, good_sqlite_path):
        conn = SQLiteConnector(good_sqlite_path, "good.db")
        conn.test_connection()
        try:
            with conn:
                raise ValueError("boom")
        except ValueError:
            pass
        assert conn._engine is None


# ---------------------------------------------------------------------------
# SQLiteConnector — file path
# ---------------------------------------------------------------------------

class TestSQLiteConnectorFromPath:
    def test_test_connection_succeeds_on_valid_db(self, good_sqlite_path):
        c = SQLiteConnector(good_sqlite_path, "good.db")
        assert c.test_connection() is True
        c.close()

    def test_get_inspector_returns_inspector(self, good_sqlite_path):
        c = SQLiteConnector(good_sqlite_path, "good.db")
        c.test_connection()
        inspector = c.get_inspector()
        assert hasattr(inspector, "get_table_names")
        c.close()

    def test_inspector_sees_tables(self, good_sqlite_path):
        c = SQLiteConnector(good_sqlite_path, "good.db")
        c.test_connection()
        tables = c.get_inspector().get_table_names()
        assert "users" in tables
        c.close()

    def test_inspector_multi_table(self, multi_table_sqlite_path):
        c = SQLiteConnector(multi_table_sqlite_path)
        c.test_connection()
        tables = c.get_inspector().get_table_names()
        assert "customers" in tables
        assert "orders" in tables
        c.close()

    def test_get_engine_returns_engine(self, good_sqlite_path):
        c = SQLiteConnector(good_sqlite_path)
        c.test_connection()
        engine = c.get_engine()
        assert engine is not None
        c.close()

    def test_get_inspector_before_test_connection_raises(self, good_sqlite_path):
        c = SQLiteConnector(good_sqlite_path)
        with pytest.raises(AnalysisError):
            c.get_inspector()

    def test_get_engine_before_test_connection_raises(self, good_sqlite_path):
        c = SQLiteConnector(good_sqlite_path)
        with pytest.raises(AnalysisError):
            c.get_engine()

    def test_close_disposes_engine(self, good_sqlite_path):
        c = SQLiteConnector(good_sqlite_path)
        c.test_connection()
        c.close()
        assert c._engine is None

    def test_close_idempotent(self, good_sqlite_path):
        c = SQLiteConnector(good_sqlite_path)
        c.test_connection()
        c.close()
        c.close()  # second close must not raise

    def test_nonexistent_path_raises_invalid_file(self, tmp_path):
        missing = str(tmp_path / "missing.db")
        with pytest.raises(InvalidFileError):
            SQLiteConnector(missing)

    def test_unsupported_extension_raises_invalid_file(self, tmp_path):
        bad = tmp_path / "file.csv"
        bad.write_text("not a database")
        with pytest.raises(InvalidFileError):
            SQLiteConnector(str(bad))

    def test_empty_db_connects_successfully(self, empty_sqlite_path):
        c = SQLiteConnector(empty_sqlite_path)
        assert c.test_connection() is True
        c.close()

    def test_source_name_property(self, good_sqlite_path):
        c = SQLiteConnector(good_sqlite_path, "my_database.db")
        assert c.source_name == "my_database.db"

    def test_db_path_property(self, good_sqlite_path):
        c = SQLiteConnector(good_sqlite_path)
        assert c.db_path == good_sqlite_path

    def test_pathlib_path_accepted(self, good_sqlite_path):
        c = SQLiteConnector(Path(good_sqlite_path))
        assert c.test_connection() is True
        c.close()


# ---------------------------------------------------------------------------
# SQLiteConnector — bytes (Streamlit upload simulation)
# ---------------------------------------------------------------------------

class TestSQLiteConnectorFromBytes:
    def test_bytes_upload_connects_successfully(self, good_sqlite_bytes):
        c = SQLiteConnector(good_sqlite_bytes, "uploaded.db")
        assert c.test_connection() is True
        c.close()

    def test_bytes_upload_creates_temp_file(self, good_sqlite_bytes):
        c = SQLiteConnector(good_sqlite_bytes, "uploaded.db")
        assert c._tmp_path is not None
        assert os.path.exists(c._tmp_path)
        c.close()

    def test_bytes_upload_temp_file_deleted_on_close(self, good_sqlite_bytes):
        c = SQLiteConnector(good_sqlite_bytes, "uploaded.db")
        tmp = c._tmp_path
        c.test_connection()
        c.close()
        assert not os.path.exists(tmp)

    def test_bytes_upload_inspector_sees_tables(self, good_sqlite_bytes):
        c = SQLiteConnector(good_sqlite_bytes, "uploaded.db")
        c.test_connection()
        assert "users" in c.get_inspector().get_table_names()
        c.close()

    def test_bytes_unsupported_extension_raises(self, good_sqlite_bytes):
        with pytest.raises(InvalidFileError):
            SQLiteConnector(good_sqlite_bytes, "data.csv")

    def test_invalid_bytes_raises_invalid_file(self):
        with pytest.raises((InvalidFileError, ConnectionError, SchemaError)):
            c = SQLiteConnector(b"this is not sqlite data", "bad.db")
            c.test_connection()

    def test_context_manager_cleans_up_temp_file(self, good_sqlite_bytes):
        c = SQLiteConnector(good_sqlite_bytes, "uploaded.db")
        tmp = c._tmp_path
        c.test_connection()
        with c:
            pass
        assert not os.path.exists(tmp)


# ---------------------------------------------------------------------------
# SQLiteConnector — read-only enforcement
# ---------------------------------------------------------------------------

class TestSQLiteReadOnly:
    def test_cannot_write_to_read_only_connection(self, good_sqlite_path):
        """SQLite opened in mode=ro must reject INSERT statements."""
        from sqlalchemy import text as sa_text
        c = SQLiteConnector(good_sqlite_path)
        c.test_connection()
        with pytest.raises(Exception):
            with c.get_engine().connect() as conn:
                conn.execute(sa_text("INSERT INTO users VALUES (99, 'Hacker')"))
                conn.commit()
        c.close()


# ---------------------------------------------------------------------------
# MySQLConnector — construction and properties
# ---------------------------------------------------------------------------

class TestMySQLConnectorConstruction:
    def _make(self, **kwargs):
        defaults = dict(
            host="localhost", database="mydb",
            username="root", password="secret",
        )
        defaults.update(kwargs)
        return MySQLConnector(**defaults)

    def test_default_port_is_3306(self):
        c = self._make()
        assert c.port == 3306

    def test_custom_port(self):
        c = self._make(port=3307)
        assert c.port == 3307

    def test_host_property(self):
        c = self._make(host="db.example.com")
        assert c.host == "db.example.com"

    def test_database_property(self):
        c = self._make(database="prod_db")
        assert c.database == "prod_db"

    def test_safe_uri_masks_password(self):
        c = self._make(password="topsecret")
        assert "topsecret" not in c.safe_uri
        assert "***" in c.safe_uri

    def test_safe_uri_preserves_host(self):
        c = self._make(host="myhost.com")
        assert "myhost.com" in c.safe_uri

    def test_safe_uri_preserves_database(self):
        c = self._make(database="mydb")
        assert "mydb" in c.safe_uri

    def test_safe_uri_preserves_username(self):
        c = self._make(username="dbuser")
        assert "dbuser" in c.safe_uri

    def test_get_inspector_before_test_raises_analysis_error(self):
        c = self._make()
        with pytest.raises(AnalysisError):
            c.get_inspector()

    def test_get_engine_before_test_raises_analysis_error(self):
        c = self._make()
        with pytest.raises(AnalysisError):
            c.get_engine()

    def test_close_without_connect_does_not_raise(self):
        c = self._make()
        c.close()  # engine is None — must not raise

    def test_close_is_idempotent(self):
        c = self._make()
        c.close()
        c.close()


# ---------------------------------------------------------------------------
# MySQLConnector — test_connection with mocked engine
# ---------------------------------------------------------------------------

class TestMySQLConnectorMocked:
    """Tests that verify error mapping without a live MySQL server."""

    def _make(self, **kwargs):
        defaults = dict(
            host="localhost", database="mydb",
            username="root", password="secret",
        )
        defaults.update(kwargs)
        return MySQLConnector(**defaults)

    def _mock_engine(self):
        engine = MagicMock()
        conn_ctx = MagicMock()
        conn_ctx.__enter__ = MagicMock(return_value=MagicMock())
        conn_ctx.__exit__ = MagicMock(return_value=False)
        engine.connect.return_value = conn_ctx
        engine.dispose = MagicMock()
        return engine

    def test_test_connection_succeeds_with_mock_engine(self):
        c = self._make()
        mock_engine = self._mock_engine()
        with patch.object(c, "_build_engine", return_value=mock_engine):
            result = c.test_connection()
        assert result is True

    def test_test_connection_stores_engine_on_success(self):
        c = self._make()
        mock_engine = self._mock_engine()
        with patch.object(c, "_build_engine", return_value=mock_engine):
            c.test_connection()
        assert c._engine is mock_engine

    def test_get_inspector_after_mock_test_connection(self):
        c = self._make()
        mock_engine = self._mock_engine()
        with patch.object(c, "_build_engine", return_value=mock_engine):
            c.test_connection()
        with patch("connectors.mysql_connector.inspect") as mock_inspect:
            mock_inspect.return_value = MagicMock()
            inspector = c.get_inspector()
            assert inspector is not None
            mock_inspect.assert_called_once_with(mock_engine)

    def test_get_engine_returns_mock_engine(self):
        c = self._make()
        mock_engine = self._mock_engine()
        with patch.object(c, "_build_engine", return_value=mock_engine):
            c.test_connection()
        assert c.get_engine() is mock_engine

    def test_close_disposes_engine(self):
        c = self._make()
        mock_engine = self._mock_engine()
        with patch.object(c, "_build_engine", return_value=mock_engine):
            c.test_connection()
        c.close()
        mock_engine.dispose.assert_called_once()
        assert c._engine is None

    def test_access_denied_raises_authentication_error(self):
        c = self._make()
        exc = Exception("(1045, \"Access denied for user 'root'@'localhost'\")")
        with patch.object(c, "_build_engine", side_effect=exc):
            with pytest.raises(AuthenticationError):
                c.test_connection()

    def test_unknown_database_raises_connection_error(self):
        c = self._make()
        exc = Exception("(1049, \"Unknown database 'mydb'\")")
        with patch.object(c, "_build_engine", side_effect=exc):
            with pytest.raises(ConnectionError):
                c.test_connection()

    def test_host_unreachable_raises_connection_error(self):
        c = self._make()
        exc = Exception("(2003, \"Can't connect to MySQL server on 'localhost'\")")
        with patch.object(c, "_build_engine", side_effect=exc):
            with pytest.raises(ConnectionError):
                c.test_connection()

    def test_connection_refused_raises_connection_error(self):
        c = self._make()
        exc = Exception("Connection refused")
        with patch.object(c, "_build_engine", side_effect=exc):
            with pytest.raises(ConnectionError):
                c.test_connection()

    def test_permission_denied_raises_permission_error(self):
        c = self._make()
        exc = Exception("(1142, \"SELECT command denied\")")
        with patch.object(c, "_build_engine", side_effect=exc):
            with pytest.raises(PermissionError):
                c.test_connection()

    def test_error_message_does_not_contain_password(self):
        c = self._make(password="ultrasecret")
        exc = Exception("Access denied for user: password=ultrasecret")
        with patch.object(c, "_build_engine", side_effect=exc):
            try:
                c.test_connection()
            except SchemaError as e:
                assert "ultrasecret" not in e.user_message

    def test_ssl_flag_passed_to_connect_args(self):
        c = self._make(ssl=True)
        args = c._build_connect_args()
        assert "ssl" in args

    def test_timeout_in_connect_args(self):
        c = self._make(timeout=30)
        args = c._build_connect_args()
        assert args["connect_timeout"] == 30

    def test_context_manager_closes_engine(self):
        c = self._make()
        mock_engine = self._mock_engine()
        with patch.object(c, "_build_engine", return_value=mock_engine):
            c.test_connection()
        with c:
            pass
        assert c._engine is None
        mock_engine.dispose.assert_called()
