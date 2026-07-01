"""Analyze endpoint — runs SQL analysis + rules and stores result in session."""
from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException, Query

import api.session_store as store
from analyzers.sql_analyzer import analyze
from exporters.json_exporter import export_json_dict
from rules.sql_rules import run_all_sql_rules
from utils.errors import SchemaError

router = APIRouter(tags=["analyze"])


@router.post("/analyze")
def run_analysis(x_session_id: str = Header(..., alias="x-session-id")):
    session = store.get(x_session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found. Please connect first.")
    if not session.connector:
        raise HTTPException(status_code=400, detail="No active connector in session.")
    try:
        inspector = session.connector.get_inspector()
        result = analyze(inspector, session.source_name, session.source_type)
        run_all_sql_rules(result)
        session.result = result
        return export_json_dict(result)
    except SchemaError as exc:
        raise HTTPException(status_code=500, detail=exc.user_message)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/debug/raw-types")
def debug_raw_types(
    x_session_id: str = Header(..., alias="x-session-id"),
    table: str = Query(default=""),
    limit: int = Query(default=5),
):
    """Return raw SQLAlchemy type strings for columns — debugging unknown types."""
    session = store.get(x_session_id)
    if not session or not session.connector:
        raise HTTPException(status_code=404, detail="No active session.")
    try:
        inspector = session.connector.get_inspector()
        tables = inspector.get_table_names()
        sample_tables = [t for t in tables if table.lower() in t.lower()][:limit] if table else tables[:limit]
        out = {}
        for tbl in sample_tables:
            cols = inspector.get_columns(tbl)
            out[tbl] = [
                {
                    "name": c["name"],
                    "type_repr": repr(c.get("type")),
                    "type_str": str(c.get("type")),
                    "type_class": type(c.get("type")).__name__,
                }
                for c in cols[:10]
            ]
        return out
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
