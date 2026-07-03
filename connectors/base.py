"""Abstract base connector shared by all database backends."""
from __future__ import annotations

from abc import ABC, abstractmethod

from sqlalchemy import Engine, Inspector


class BaseConnector(ABC):
    """Read-only database connector contract.

    Subclasses must implement test_connection, get_inspector, and close.
    The tool never performs write operations — only SELECT / PRAGMA / metadata
    queries are permitted.
    """

    @abstractmethod
    def test_connection(self) -> bool:
        """Verify the database is reachable and readable.

        Returns True on success.
        Raises a subclass of SchemaError on failure.
        """

    @abstractmethod
    def get_inspector(self) -> Inspector:
        """Return a SQLAlchemy Inspector bound to the live engine.

        Must be called only after test_connection() succeeds.
        """

    @abstractmethod
    def get_engine(self) -> Engine:
        """Return the underlying SQLAlchemy Engine."""

    @abstractmethod
    def close(self) -> None:
        """Dispose the engine and release any temporary resources."""

    # ------------------------------------------------------------------
    # Context-manager support so connectors can be used with `with`
    # ------------------------------------------------------------------

    def __enter__(self) -> "BaseConnector":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
