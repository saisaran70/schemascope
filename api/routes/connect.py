"""Connect / disconnect endpoints."""
from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from pydantic import BaseModel

import api.session_store as store
from connectors.mysql_connector import MySQLConnector
from connectors.sqlite_connector import SQLiteConnector
from models.schema_models import (
    AnalysisResult, EntityInfo, FieldInfo, Finding, RelationshipInfo,
)
from utils.errors import SchemaError

router = APIRouter(tags=["connect"])


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

class MySQLParams(BaseModel):
    host: str
    database: str
    username: str
    password: str
    port: int = 3306
    ssl: bool = False
    timeout: int = 10


class ConnectResponse(BaseModel):
    session_id: str
    source_name: str
    source_type: str
    message: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/connect/sqlite", response_model=ConnectResponse)
async def connect_sqlite(file: UploadFile = File(...)):
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    filename = file.filename or "upload.db"
    try:
        connector = SQLiteConnector(source=content, source_name=filename)
        connector.test_connection()
    except SchemaError as exc:
        raise HTTPException(status_code=400, detail=exc.user_message)
    session_id = str(uuid.uuid4())
    store.create(session_id, filename, "sqlite", connector)
    return ConnectResponse(
        session_id=session_id,
        source_name=filename,
        source_type="sqlite",
        message="Connected successfully.",
    )


@router.post("/connect/mysql", response_model=ConnectResponse)
def connect_mysql(params: MySQLParams):
    try:
        connector = MySQLConnector(
            host=params.host,
            database=params.database,
            username=params.username,
            password=params.password,
            port=params.port,
            ssl=params.ssl,
            timeout=params.timeout,
        )
        connector.test_connection()
    except SchemaError as exc:
        raise HTTPException(status_code=503, detail=exc.user_message)
    session_id = str(uuid.uuid4())
    store.create(session_id, params.database, "mysql", connector)
    return ConnectResponse(
        session_id=session_id,
        source_name=params.database,
        source_type="mysql",
        message="Connected successfully.",
    )


@router.delete("/sessions/{session_id}")
def disconnect(session_id: str):
    store.delete(session_id)
    return {"message": "Session cleared."}


@router.post("/sessions/restore", response_model=ConnectResponse)
async def restore_session(request: Request):
    """Recreate a server session from a previously exported analysis JSON.

    The frontend sends the cached analysis_metadata + entities + relationships +
    findings + warnings payload (the same shape as /analyze returns).  The server
    reconstructs an AnalysisResult in memory so all diagram / export endpoints
    work without re-running the analysis.
    """
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body.")
    try:
        result = _parse_result(data)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Could not parse cached result: {exc}")
    session_id = str(uuid.uuid4())
    session = store.create(session_id, result.source_name, result.source_type)
    session.result = result
    return ConnectResponse(
        session_id=session_id,
        source_name=result.source_name,
        source_type=result.source_type,
        message="Session restored from cache.",
    )


# ---------------------------------------------------------------------------
# Result reconstruction helpers (used by /sessions/restore)
# ---------------------------------------------------------------------------

def _parse_result(data: dict[str, Any]) -> AnalysisResult:
    meta = data.get("analysis_metadata", {})
    return AnalysisResult(
        source_type=meta.get("source_type", "sqlite"),
        source_name=meta.get("source_name", ""),
        analysed_at=meta.get("analysed_at", ""),
        entities=[_parse_entity(e) for e in data.get("entities", [])],
        relationships=[_parse_relationship(r) for r in data.get("relationships", [])],
        findings=[_parse_finding(f) for f in data.get("findings", [])],
        warnings=data.get("warnings", []),
    )


def _parse_entity(d: dict[str, Any]) -> EntityInfo:
    return EntityInfo(
        name=d["name"],
        entity_type=d.get("entity_type", "table"),
        fields=[_parse_field(f) for f in d.get("fields", [])],
        indexes=d.get("indexes", []),
        row_count=d.get("row_count"),
        metadata=d.get("metadata", {}),
    )


def _parse_field(d: dict[str, Any]) -> FieldInfo:
    return FieldInfo(
        name=d["name"],
        data_type=d.get("data_type", "text"),
        nullable=d.get("nullable", True),
        primary_key=d.get("primary_key", False),
        unique=d.get("unique", False),
        default_value=d.get("default_value"),
        foreign_key_target=d.get("foreign_key_target"),
        indexed=d.get("indexed", False),
        index_names=d.get("index_names", []),
    )


def _parse_relationship(d: dict[str, Any]) -> RelationshipInfo:
    return RelationshipInfo(
        source_entity=d["source_entity"],
        source_field=d["source_field"],
        target_entity=d["target_entity"],
        target_field=d.get("target_field", ""),
        declared=d.get("declared", False),
        confidence=d.get("confidence", 1.0),
        evidence=d.get("evidence", []),
    )


def _parse_finding(d: dict[str, Any]) -> Finding:
    return Finding(
        rule_id=d["rule_id"],
        database_type=d.get("database_type", "sqlite"),
        entity=d.get("entity", ""),
        field=d.get("field"),
        severity=d.get("severity", "low"),
        confidence=d.get("confidence", 1.0),
        title=d.get("title", ""),
        description=d.get("description", ""),
        evidence=d.get("evidence", []),
        impact=d.get("impact", ""),
        recommendation=d.get("recommendation", ""),
        suggested_command=d.get("suggested_command"),
        review_status=d.get("review_status", "open"),
    )
