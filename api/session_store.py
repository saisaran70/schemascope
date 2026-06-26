"""In-memory session store for the local single-user SchemaScope API.

Each session holds one active connector and (after /analyze) one AnalysisResult.
The store is a plain dict — safe for uvicorn's default single-worker mode.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from connectors.base import BaseConnector
from models.schema_models import AnalysisResult

_store: dict[str, "Session"] = {}


@dataclass
class Session:
    session_id: str
    source_name: str = ""
    source_type: str = "sqlite"
    connector: Optional[BaseConnector] = None
    result: Optional[AnalysisResult] = None


def create(
    session_id: str,
    source_name: str,
    source_type: str,
    connector: Optional[BaseConnector] = None,
) -> Session:
    s = Session(
        session_id=session_id,
        source_name=source_name,
        source_type=source_type,
        connector=connector,
    )
    _store[session_id] = s
    return s


def get(session_id: str) -> Optional[Session]:
    return _store.get(session_id)


def delete(session_id: str) -> None:
    s = _store.pop(session_id, None)
    if s and s.connector:
        try:
            s.connector.close()
        except Exception:
            pass
