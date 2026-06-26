"""Export endpoints — markdown, JSON, and Mermaid diagram."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Header, HTTPException, Query
from fastapi.responses import Response

import api.session_store as store
from exporters.json_exporter import export_json
from exporters.markdown_exporter import export_markdown, generate_export_filename
from visualizers.mermaid_generator import generate_er_diagram

router = APIRouter(tags=["export"])


def _require_result(session_id: str):
    session = store.get(session_id)
    if not session or not session.result:
        raise HTTPException(
            status_code=404,
            detail="No analysis result found. Run /analyze first.",
        )
    return session.result


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")


@router.get("/export/markdown")
def download_markdown(x_session_id: str = Header(..., alias="x-session-id")):
    result = _require_result(x_session_id)
    filename = generate_export_filename(result.source_name, _ts(), "report.md")
    content = export_markdown(result)
    return Response(
        content=content,
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/export/json")
def download_json(x_session_id: str = Header(..., alias="x-session-id")):
    result = _require_result(x_session_id)
    filename = generate_export_filename(result.source_name, _ts(), "analysis.json")
    content = export_json(result)
    return Response(
        content=content,
        media_type="application/json; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/export/mermaid")
def download_mermaid(x_session_id: str = Header(..., alias="x-session-id")):
    result = _require_result(x_session_id)
    filename = generate_export_filename(result.source_name, _ts(), "diagram.mmd")
    # No entity limit for file download — export the full schema.
    content = generate_er_diagram(result, max_entities=len(result.entities) + 1)
    return Response(
        content=content,
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/diagram")
def get_diagram(
    x_session_id: str = Header(..., alias="x-session-id"),
    entities: list[str] = Query(default=[]),
    max_entities: int = Query(default=200),
):
    """Return Mermaid source for rendering in the browser.

    Differs from /export/mermaid in two ways:
    - No Content-Disposition header (plain text for inline rendering)
    - Accepts ?entities=t1&entities=t2 filter and a higher max_entities default
    """
    result = _require_result(x_session_id)
    selected = entities if entities else None
    content = generate_er_diagram(result, selected_entities=selected, max_entities=max_entities)
    return Response(content=content, media_type="text/plain; charset=utf-8")
