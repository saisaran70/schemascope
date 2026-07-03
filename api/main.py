"""SchemaScope FastAPI application entry point.

Run from schema_scope/ directory:
    uvicorn api.main:app --reload --port 8000
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes.analyze import router as analyze_router
from api.routes.connect import router as connect_router
from api.routes.export import router as export_router

app = FastAPI(
    title="SchemaScope API",
    version="1.0.0",
    description="Read-only database schema analysis API.",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(connect_router, prefix="/api")
app.include_router(analyze_router, prefix="/api")
app.include_router(export_router, prefix="/api")


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "SchemaScope", "version": "1.0.0"}
