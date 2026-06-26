"""Custom exception hierarchy and user-facing error messages (PRD §11.6)."""
from __future__ import annotations


class SchemaError(Exception):
    """Base exception for all SchemaScope errors."""

    def __init__(self, message: str, technical_detail: str = ""):
        super().__init__(message)
        self.user_message = message
        self.technical_detail = technical_detail

    def __str__(self) -> str:
        return self.user_message


class ConnectionError(SchemaError):
    """Raised when the database cannot be reached or opened."""


class AuthenticationError(SchemaError):
    """Raised when credentials are rejected."""


class PermissionError(SchemaError):
    """Raised when the account lacks the required read permissions."""


class InvalidFileError(SchemaError):
    """Raised when the uploaded file is not a valid database."""


class AnalysisError(SchemaError):
    """Raised when schema metadata extraction fails."""


class ExportError(SchemaError):
    """Raised when report generation or serialization fails."""


class DependencyError(SchemaError):
    """Raised when a required Python driver is missing."""


# ---------------------------------------------------------------------------
# Error code → user-facing message map (PRD §11.6)
# ---------------------------------------------------------------------------

ERROR_MESSAGES: dict[str, str] = {
    "invalid_sqlite_file": "The file is not a valid or readable SQLite database.",
    "unsupported_extension": "Upload a .db, .sqlite, or .sqlite3 file.",
    "file_locked": "Close applications holding an exclusive lock and retry.",
    "auth_failed": "Verify the username, password, and permissions.",
    "host_unreachable": "Verify host, port, network, and VPN access.",
    "database_not_found": "Verify the database name.",
    "mongodb_uri_invalid": "Verify URI format and encoded special characters.",
    "permission_denied": "Use an account allowed to read schema metadata.",
    "driver_missing": "Install the required Python driver and restart the application.",
    "timeout": "Increase the timeout or verify network access.",
}


def user_message_for(error_code: str, fallback: str = "An unexpected error occurred.") -> str:
    """Return the user-facing message for a known error code."""
    return ERROR_MESSAGES.get(error_code, fallback)
