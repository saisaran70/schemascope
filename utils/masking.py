"""Credential masking utilities (PRD §24).

Rules:
- Never write passwords or full connection URIs to logs or exports.
- Show masked connection information.
- Credentials remain only in session memory.
"""
from __future__ import annotations

import re

# Matches password segment in URIs: scheme://user:PASSWORD@host
_URI_PASSWORD_RE = re.compile(
    r"((?:mysql|mongodb(?:\+srv)?|postgresql|postgres|sqlite)\+?\w*://"
    r"[^:@/]+:)([^@]+)(@)",
    re.IGNORECASE,
)

# Matches standalone key=value patterns (password=secret, pwd=secret)
_KV_PASSWORD_RE = re.compile(
    r"((?:password|passwd|pwd|secret)\s*=\s*)([^\s;,&]+)",
    re.IGNORECASE,
)

MASK = "***"


def mask_uri(uri: str) -> str:
    """Replace the password portion of a connection URI with '***'.

    Examples
    --------
    mask_uri("mysql://user:s3cr3t@localhost/db")
    -> "mysql://user:***@localhost/db"

    mask_uri("mongodb://admin:p%40ss@cluster.net/mydb")
    -> "mongodb://admin:***@cluster.net/mydb"
    """
    return _URI_PASSWORD_RE.sub(r"\1" + MASK + r"\3", uri)


def mask_kv(text: str) -> str:
    """Replace password= / pwd= values with '***' in key=value strings."""
    return _KV_PASSWORD_RE.sub(r"\g<1>" + MASK, text)


def mask_connection_string(text: str) -> str:
    """Apply all masking rules to *text* (URI or key=value or mixed)."""
    text = mask_uri(text)
    text = mask_kv(text)
    return text


def safe_source_name(source_name: str) -> str:
    """Return a display-safe label for a source (file name or db name).

    Strips any leading path components so only the file/db name is shown.
    """
    # Keep only the last path segment (works for both / and \)
    for sep in ("/", "\\"):
        if sep in source_name:
            source_name = source_name.rsplit(sep, 1)[-1]
    return source_name
