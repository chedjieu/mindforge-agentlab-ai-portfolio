"""Upload allowlist — malware scanning boundary (ClamAV in production)."""

from __future__ import annotations

ALLOWED_MIME = {
    "application/pdf",
    "text/plain",
    "text/markdown",
    "application/octet-stream",
}
ALLOWED_EXT = {".pdf", ".txt", ".md"}


def validate_upload(filename: str, content_type: str | None, size: int, max_bytes: int) -> None:
    from pathlib import Path

    from fastapi import HTTPException

    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXT:
        raise HTTPException(400, f"Extension {ext} not allowed")
    if size > max_bytes:
        raise HTTPException(413, "File too large")
    if content_type and content_type.split(";")[0].strip() not in ALLOWED_MIME:
        if ext not in ALLOWED_EXT:
            raise HTTPException(400, f"MIME {content_type} not allowed")
