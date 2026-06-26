"""SQLite connector — read-only, supports file upload (bytes) or file path."""
from __future__ import annotations

import os
import sqlite3
import tempfile
from pathlib import Path

from sqlalchemy import Engine, Inspector, create_engine, inspect, text
from sqlalchemy.pool import StaticPool

from connectors.base import BaseConnector
from utils.errors import (
    AnalysisError,
    ConnectionError,
    InvalidFileError,
    PermissionError,
)

_SUPPORTED_EXTENSIONS = {".db", ".sqlite", ".sqlite3"}


class SQLiteConnector(BaseConnector):
    """Connect to a SQLite database from a file path or raw bytes.

    Parameters
    ----------
    source:
        Either a filesystem path (str / Path) or raw bytes from a file
        upload (e.g. Streamlit's UploadedFile.read()).
    source_name:
        Display label used in reports (e.g. the original filename).
    """

    def __init__(self, source: str | Path | bytes, source_name: str = "database.db"):
        self._source_name = source_name
        self._tmp_path: str | None = None
        self._engine: Engine | None = None
        self._db_path: str = self._resolve_path(source)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_path(self, source: str | Path | bytes) -> str:
        if isinstance(source, bytes):
            return self._write_temp_file(source)
        path = Path(source)
        self._validate_extension(path)
        if not path.exists():
            raise InvalidFileError(
                "The file is not a valid or readable SQLite database.",
                technical_detail=f"Path not found: {path}",
            )
        return str(path)

    def _write_temp_file(self, data: bytes) -> str:
        suffix = Path(self._source_name).suffix or ".db"
        self._validate_extension(Path(self._source_name))
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        try:
            tmp.write(data)
            tmp.flush()
        finally:
            tmp.close()
        self._tmp_path = tmp.name
        return tmp.name

    @staticmethod
    def _validate_extension(path: Path) -> None:
        if path.suffix.lower() not in _SUPPORTED_EXTENSIONS:
            raise InvalidFileError(
                "Upload a .db, .sqlite, or .sqlite3 file.",
                technical_detail=f"Unsupported extension: {path.suffix!r}",
            )

    def _build_engine(self) -> Engine:
        # Use pathlib.as_uri() to produce a correct file:/// URI on all
        # platforms (especially Windows backslash paths), then pass it
        # directly to sqlite3 via a creator function so SQLAlchemy's own
        # URI parser never sees the Windows path.
        file_uri = Path(self._db_path).as_uri() + "?mode=ro"

        def _creator():
            return sqlite3.connect(file_uri, uri=True)

        return create_engine(
            "sqlite+pysqlite://",
            creator=_creator,
            poolclass=StaticPool,
            connect_args={"check_same_thread": False},
            echo=False,
        )

    # ------------------------------------------------------------------
    # BaseConnector interface
    # ------------------------------------------------------------------

    def test_connection(self) -> bool:
        """Open the database and run a trivial query to confirm readability."""
        try:
            engine = self._build_engine()
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            # Keep the engine for subsequent get_inspector() calls
            if self._engine:
                self._engine.dispose()
            self._engine = engine
            return True
        except InvalidFileError:
            raise
        except Exception as exc:
            msg = str(exc).lower()
            if "unable to open" in msg or "no such file" in msg:
                raise InvalidFileError(
                    "The file is not a valid or readable SQLite database.",
                    technical_detail=str(exc),
                )
            if "locked" in msg:
                raise ConnectionError(
                    "Close applications holding an exclusive lock and retry.",
                    technical_detail=str(exc),
                )
            if "permission" in msg or "access" in msg:
                raise PermissionError(
                    "Use an account allowed to read schema metadata.",
                    technical_detail=str(exc),
                )
            raise ConnectionError(
                "The file is not a valid or readable SQLite database.",
                technical_detail=str(exc),
            )

    def get_inspector(self) -> Inspector:
        if self._engine is None:
            raise AnalysisError(
                "Call test_connection() before get_inspector().",
                technical_detail="Engine not initialised.",
            )
        return inspect(self._engine)

    def get_engine(self) -> Engine:
        if self._engine is None:
            raise AnalysisError(
                "Call test_connection() before get_engine().",
                technical_detail="Engine not initialised.",
            )
        return self._engine

    def close(self) -> None:
        if self._engine:
            self._engine.dispose()
            self._engine = None
        if self._tmp_path and os.path.exists(self._tmp_path):
            os.remove(self._tmp_path)
            self._tmp_path = None

    # ------------------------------------------------------------------
    # Read-only enforcement helpers
    # ------------------------------------------------------------------

    @property
    def source_name(self) -> str:
        return self._source_name

    @property
    def db_path(self) -> str:
        return self._db_path
