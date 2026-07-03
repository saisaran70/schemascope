"""MySQL connector — read-only, compatible with MySQL Workbench databases."""
from __future__ import annotations

from sqlalchemy import Engine, Inspector, create_engine, inspect, text
from sqlalchemy.exc import OperationalError as SAOperationalError

from connectors.base import BaseConnector
from utils.errors import (
    AnalysisError,
    AuthenticationError,
    ConnectionError,
    DependencyError,
    PermissionError,
)
from utils.masking import mask_uri

_DEFAULT_PORT = 3306
_DEFAULT_TIMEOUT = 10  # seconds


class MySQLConnector(BaseConnector):
    """Connect to a MySQL / MySQL Workbench database via PyMySQL.

    Parameters
    ----------
    host:       Hostname or IP of the MySQL server.
    database:   Database (schema) name.
    username:   MySQL user account.
    password:   Password (kept only in memory, never logged).
    port:       TCP port — defaults to 3306.
    ssl:        When True, require SSL/TLS for the connection.
    timeout:    Connection timeout in seconds — defaults to 10.
    """

    def __init__(
        self,
        host: str,
        database: str,
        username: str,
        password: str,
        port: int = _DEFAULT_PORT,
        ssl: bool = False,
        timeout: int = _DEFAULT_TIMEOUT,
    ):
        self._host = host
        self._database = database
        self._username = username
        self._password = password
        self._port = port
        self._ssl = ssl
        self._timeout = timeout
        self._engine: Engine | None = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_uri(self) -> str:
        return (
            f"mysql+pymysql://{self._username}:{self._password}"
            f"@{self._host}:{self._port}/{self._database}"
        )

    def _safe_uri(self) -> str:
        """Masked URI safe for logging and error messages."""
        return mask_uri(self._build_uri())

    def _build_connect_args(self) -> dict:
        args: dict = {"connect_timeout": self._timeout}
        if self._ssl:
            args["ssl"] = {"ssl_disabled": False}
        return args

    def _build_engine(self) -> Engine:
        try:
            return create_engine(
                self._build_uri(),
                connect_args=self._build_connect_args(),
                echo=False,
                pool_pre_ping=True,
            )
        except Exception as exc:
            if "no module named" in str(exc).lower():
                raise DependencyError(
                    "Install the required Python driver and restart the application.",
                    technical_detail=str(exc),
                )
            raise ConnectionError(
                "Verify host, port, network, and VPN access.",
                technical_detail=str(exc),
            )

    def _map_error(self, exc: Exception) -> None:
        """Map a SQLAlchemy / PyMySQL exception to a SchemaError subclass."""
        msg = str(exc).lower()

        if "no module named" in msg or "modulenotfounderror" in msg:
            raise DependencyError(
                "Install the required Python driver and restart the application.",
                technical_detail=str(exc),
            )
        if (
            "access denied" in msg
            or "authentication" in msg
            or "password" in msg
            or "1045" in msg  # ER_ACCESS_DENIED_ERROR
        ):
            raise AuthenticationError(
                "Verify the username, password, and permissions.",
                technical_detail=str(exc),
            )
        if (
            "unknown database" in msg
            or "1049" in msg  # ER_BAD_DB_ERROR
        ):
            raise ConnectionError(
                "Verify the database name.",
                technical_detail=str(exc),
            )
        if (
            "can't connect" in msg
            or "connection refused" in msg
            or "timed out" in msg
            or "2003" in msg  # CR_CONN_HOST_ERROR
            or "2013" in msg  # CR_SERVER_LOST
        ):
            raise ConnectionError(
                "Verify host, port, network, and VPN access.",
                technical_detail=str(exc),
            )
        if "permission" in msg or "command denied" in msg or "1142" in msg:
            raise PermissionError(
                "Use an account allowed to read schema metadata.",
                technical_detail=str(exc),
            )
        raise ConnectionError(
            "Verify host, port, network, and VPN access.",
            technical_detail=str(exc),
        )

    # ------------------------------------------------------------------
    # BaseConnector interface
    # ------------------------------------------------------------------

    def test_connection(self) -> bool:
        """Open a connection to MySQL and run SELECT 1."""
        try:
            engine = self._build_engine()
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            if self._engine:
                self._engine.dispose()
            self._engine = engine
            return True
        except (AuthenticationError, ConnectionError, PermissionError, DependencyError):
            raise
        except SAOperationalError as exc:
            self._map_error(exc)
        except Exception as exc:
            self._map_error(exc)

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

    # ------------------------------------------------------------------
    # Properties — never expose raw password
    # ------------------------------------------------------------------

    @property
    def safe_uri(self) -> str:
        return self._safe_uri()

    @property
    def host(self) -> str:
        return self._host

    @property
    def database(self) -> str:
        return self._database

    @property
    def port(self) -> int:
        return self._port
