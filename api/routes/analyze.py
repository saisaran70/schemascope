"""Analyze endpoint — runs SQL analysis + rules and stores result in session."""
from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException

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
