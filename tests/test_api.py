"""Integration tests for the FastAPI backend (Step 8).

Uses FastAPI's TestClient (synchronous httpx-based).
All tests use a real in-memory SQLite database — no live MySQL server needed.
"""
from __future__ import annotations

import json
import os
import sqlite3
import tempfile

import pytest
from fastapi.testclient import TestClient

import api.session_store as store
from api.main import app


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def clear_session_store():
    """Reset the in-memory store between every test."""
    for sid in list(store._store.keys()):
        store.delete(sid)
    yield
    for sid in list(store._store.keys()):
        store.delete(sid)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def sqlite_bytes():
    """Bytes of a minimal SQLite database with users + orders tables."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    conn = sqlite3.connect(path)
    conn.executescript("""
        CREATE TABLE users (
            id    INTEGER PRIMARY KEY,
            name  TEXT NOT NULL,
            email TEXT
        );
        CREATE TABLE orders (
            id         INTEGER PRIMARY KEY,
            user_id    INTEGER,
            total      REAL,
            created_at TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
        CREATE INDEX idx_orders_user ON orders(user_id);
    """)
    conn.commit()
    conn.close()
    with open(path, "rb") as f:
        data = f.read()
    os.unlink(path)
    return data


@pytest.fixture
def connected_session(client, sqlite_bytes):
    """Returns session_id after a successful SQLite connect."""
    resp = client.post(
        "/api/connect/sqlite",
        files={"file": ("test.db", sqlite_bytes, "application/octet-stream")},
    )
    assert resp.status_code == 200
    return resp.json()["session_id"]


@pytest.fixture
def analyzed_session(client, connected_session):
    """Returns session_id after connect + analyze."""
    resp = client.post("/api/analyze", headers={"x-session-id": connected_session})
    assert resp.status_code == 200
    return connected_session


# ===========================================================================
# Health
# ===========================================================================

class TestHealth:
    def test_health_ok(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_health_service_name(self, client):
        resp = client.get("/api/health")
        assert resp.json()["service"] == "SchemaScope"


# ===========================================================================
# SQLite connect
# ===========================================================================

class TestConnectSQLite:
    def test_successful_connect(self, client, sqlite_bytes):
        resp = client.post(
            "/api/connect/sqlite",
            files={"file": ("mydb.db", sqlite_bytes, "application/octet-stream")},
        )
        assert resp.status_code == 200

    def test_response_has_session_id(self, client, sqlite_bytes):
        resp = client.post(
            "/api/connect/sqlite",
            files={"file": ("mydb.db", sqlite_bytes, "application/octet-stream")},
        )
        assert "session_id" in resp.json()
        assert len(resp.json()["session_id"]) == 36  # UUID4

    def test_response_source_type_sqlite(self, client, sqlite_bytes):
        resp = client.post(
            "/api/connect/sqlite",
            files={"file": ("mydb.db", sqlite_bytes, "application/octet-stream")},
        )
        assert resp.json()["source_type"] == "sqlite"

    def test_response_source_name(self, client, sqlite_bytes):
        resp = client.post(
            "/api/connect/sqlite",
            files={"file": ("mydb.db", sqlite_bytes, "application/octet-stream")},
        )
        assert resp.json()["source_name"] == "mydb.db"

    def test_empty_file_rejected(self, client):
        resp = client.post(
            "/api/connect/sqlite",
            files={"file": ("empty.db", b"", "application/octet-stream")},
        )
        assert resp.status_code == 400

    def test_invalid_extension_rejected(self, client):
        resp = client.post(
            "/api/connect/sqlite",
            files={"file": ("data.csv", b"some,data", "text/csv")},
        )
        assert resp.status_code in (400, 422)

    def test_session_stored_after_connect(self, client, sqlite_bytes):
        resp = client.post(
            "/api/connect/sqlite",
            files={"file": ("test.db", sqlite_bytes, "application/octet-stream")},
        )
        sid = resp.json()["session_id"]
        assert store.get(sid) is not None

    def test_two_connects_create_separate_sessions(self, client, sqlite_bytes):
        r1 = client.post(
            "/api/connect/sqlite",
            files={"file": ("a.db", sqlite_bytes, "application/octet-stream")},
        )
        r2 = client.post(
            "/api/connect/sqlite",
            files={"file": ("b.db", sqlite_bytes, "application/octet-stream")},
        )
        assert r1.json()["session_id"] != r2.json()["session_id"]


# ===========================================================================
# MySQL connect (mocked — no live server)
# ===========================================================================

class TestConnectMySQL:
    def test_mysql_bad_host_returns_503(self, client):
        resp = client.post(
            "/api/connect/mysql",
            json={
                "host": "127.0.0.1",
                "database": "nonexistent",
                "username": "root",
                "password": "wrong",
                "port": 19999,
            },
        )
        assert resp.status_code == 503

    def test_mysql_missing_fields_returns_422(self, client):
        resp = client.post("/api/connect/mysql", json={"host": "localhost"})
        assert resp.status_code == 422


# ===========================================================================
# Disconnect
# ===========================================================================

class TestDisconnect:
    def test_disconnect_removes_session(self, client, connected_session):
        resp = client.delete(f"/api/sessions/{connected_session}")
        assert resp.status_code == 200
        assert store.get(connected_session) is None

    def test_disconnect_unknown_session_ok(self, client):
        resp = client.delete("/api/sessions/nonexistent-uuid")
        assert resp.status_code == 200


# ===========================================================================
# Analyze
# ===========================================================================

class TestAnalyze:
    def test_analyze_success(self, client, connected_session):
        resp = client.post("/api/analyze", headers={"x-session-id": connected_session})
        assert resp.status_code == 200

    def test_analyze_returns_analysis_metadata(self, client, connected_session):
        resp = client.post("/api/analyze", headers={"x-session-id": connected_session})
        data = resp.json()
        assert "analysis_metadata" in data

    def test_analyze_returns_entities(self, client, connected_session):
        resp = client.post("/api/analyze", headers={"x-session-id": connected_session})
        data = resp.json()
        assert "entities" in data
        assert isinstance(data["entities"], list)

    def test_analyze_finds_users_table(self, client, connected_session):
        resp = client.post("/api/analyze", headers={"x-session-id": connected_session})
        names = [e["name"] for e in resp.json()["entities"]]
        assert "users" in names

    def test_analyze_finds_orders_table(self, client, connected_session):
        resp = client.post("/api/analyze", headers={"x-session-id": connected_session})
        names = [e["name"] for e in resp.json()["entities"]]
        assert "orders" in names

    def test_analyze_returns_relationships(self, client, connected_session):
        resp = client.post("/api/analyze", headers={"x-session-id": connected_session})
        data = resp.json()
        assert "relationships" in data
        assert isinstance(data["relationships"], list)

    def test_analyze_detects_fk_relationship(self, client, connected_session):
        resp = client.post("/api/analyze", headers={"x-session-id": connected_session})
        rels = resp.json()["relationships"]
        assert any(r["source_entity"] == "orders" and r["target_entity"] == "users" for r in rels)

    def test_analyze_returns_findings(self, client, connected_session):
        resp = client.post("/api/analyze", headers={"x-session-id": connected_session})
        data = resp.json()
        assert "findings" in data
        assert isinstance(data["findings"], list)

    def test_analyze_returns_warnings(self, client, connected_session):
        resp = client.post("/api/analyze", headers={"x-session-id": connected_session})
        data = resp.json()
        assert "warnings" in data

    def test_analyze_metadata_source_type(self, client, connected_session):
        resp = client.post("/api/analyze", headers={"x-session-id": connected_session})
        meta = resp.json()["analysis_metadata"]
        assert meta["source_type"] == "sqlite"

    def test_analyze_stores_result_in_session(self, client, connected_session):
        client.post("/api/analyze", headers={"x-session-id": connected_session})
        session = store.get(connected_session)
        assert session is not None
        assert session.result is not None

    def test_analyze_unknown_session_404(self, client):
        resp = client.post("/api/analyze", headers={"x-session-id": "no-such-session"})
        assert resp.status_code == 404

    def test_analyze_missing_header_422(self, client):
        resp = client.post("/api/analyze")
        assert resp.status_code == 422

    def test_analyze_entity_fields_present(self, client, connected_session):
        resp = client.post("/api/analyze", headers={"x-session-id": connected_session})
        users = next(e for e in resp.json()["entities"] if e["name"] == "users")
        field_names = [f["name"] for f in users["fields"]]
        assert "id" in field_names
        assert "name" in field_names

    def test_analyze_pk_detected(self, client, connected_session):
        resp = client.post("/api/analyze", headers={"x-session-id": connected_session})
        users = next(e for e in resp.json()["entities"] if e["name"] == "users")
        id_field = next(f for f in users["fields"] if f["name"] == "id")
        assert id_field["primary_key"] is True


# ===========================================================================
# Exports
# ===========================================================================

class TestExportMarkdown:
    def test_markdown_200(self, client, analyzed_session):
        resp = client.get("/api/export/markdown", headers={"x-session-id": analyzed_session})
        assert resp.status_code == 200

    def test_markdown_content_type(self, client, analyzed_session):
        resp = client.get("/api/export/markdown", headers={"x-session-id": analyzed_session})
        assert "text/markdown" in resp.headers["content-type"]

    def test_markdown_has_h1(self, client, analyzed_session):
        resp = client.get("/api/export/markdown", headers={"x-session-id": analyzed_session})
        assert resp.text.startswith("# SchemaScope")

    def test_markdown_contains_table_name(self, client, analyzed_session):
        resp = client.get("/api/export/markdown", headers={"x-session-id": analyzed_session})
        assert "users" in resp.text

    def test_markdown_content_disposition(self, client, analyzed_session):
        resp = client.get("/api/export/markdown", headers={"x-session-id": analyzed_session})
        assert "attachment" in resp.headers.get("content-disposition", "")

    def test_markdown_no_analysis_404(self, client, connected_session):
        resp = client.get("/api/export/markdown", headers={"x-session-id": connected_session})
        assert resp.status_code == 404

    def test_markdown_unknown_session_404(self, client):
        resp = client.get("/api/export/markdown", headers={"x-session-id": "no-session"})
        assert resp.status_code == 404


class TestExportJSON:
    def test_json_200(self, client, analyzed_session):
        resp = client.get("/api/export/json", headers={"x-session-id": analyzed_session})
        assert resp.status_code == 200

    def test_json_valid(self, client, analyzed_session):
        resp = client.get("/api/export/json", headers={"x-session-id": analyzed_session})
        parsed = json.loads(resp.text)
        assert isinstance(parsed, dict)

    def test_json_has_entities_key(self, client, analyzed_session):
        resp = client.get("/api/export/json", headers={"x-session-id": analyzed_session})
        assert "entities" in json.loads(resp.text)

    def test_json_content_disposition(self, client, analyzed_session):
        resp = client.get("/api/export/json", headers={"x-session-id": analyzed_session})
        assert "attachment" in resp.headers.get("content-disposition", "")

    def test_json_no_analysis_404(self, client, connected_session):
        resp = client.get("/api/export/json", headers={"x-session-id": connected_session})
        assert resp.status_code == 404


class TestExportMermaid:
    def test_mermaid_200(self, client, analyzed_session):
        resp = client.get("/api/export/mermaid", headers={"x-session-id": analyzed_session})
        assert resp.status_code == 200

    def test_mermaid_starts_with_erdiagram(self, client, analyzed_session):
        resp = client.get("/api/export/mermaid", headers={"x-session-id": analyzed_session})
        assert resp.text.strip().startswith("erDiagram")

    def test_mermaid_content_disposition(self, client, analyzed_session):
        resp = client.get("/api/export/mermaid", headers={"x-session-id": analyzed_session})
        assert "attachment" in resp.headers.get("content-disposition", "")

    def test_mermaid_no_analysis_404(self, client, connected_session):
        resp = client.get("/api/export/mermaid", headers={"x-session-id": connected_session})
        assert resp.status_code == 404


# ===========================================================================
# End-to-end flow
# ===========================================================================

class TestEndToEnd:
    def test_full_flow(self, client, sqlite_bytes):
        """Connect → Analyze → Export markdown, JSON, mermaid all succeed."""
        # 1. Connect
        r1 = client.post(
            "/api/connect/sqlite",
            files={"file": ("e2e.db", sqlite_bytes, "application/octet-stream")},
        )
        assert r1.status_code == 200
        sid = r1.json()["session_id"]

        # 2. Analyze
        r2 = client.post("/api/analyze", headers={"x-session-id": sid})
        assert r2.status_code == 200

        # 3. Exports
        for path in ("/api/export/markdown", "/api/export/json", "/api/export/mermaid"):
            r = client.get(path, headers={"x-session-id": sid})
            assert r.status_code == 200, f"{path} failed"

        # 4. Disconnect
        r4 = client.delete(f"/api/sessions/{sid}")
        assert r4.status_code == 200
        assert store.get(sid) is None

    def test_analyze_before_connect_fails(self, client):
        resp = client.post("/api/analyze", headers={"x-session-id": "ghost-session"})
        assert resp.status_code == 404

    def test_export_before_analyze_fails(self, client, connected_session):
        for path in ("/api/export/markdown", "/api/export/json", "/api/export/mermaid"):
            resp = client.get(path, headers={"x-session-id": connected_session})
            assert resp.status_code == 404, f"{path} should 404 before analyze"
