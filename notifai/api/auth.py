"""API key authentication for NotifAI."""

from __future__ import annotations

import secrets
from typing import Annotated

from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader

from notifai.config.settings import settings

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(
    api_key: Annotated[str | None, Security(api_key_header)],
) -> str:
    """Verify the API key from the X-API-Key header.

    If API_KEY is not set in settings, authentication is disabled (dev mode).
    """
    if not settings.api_key:
        return "dev-mode"

    if not api_key:
        raise HTTPException(status_code=401, detail="Missing API key")

    if not secrets.compare_digest(api_key, settings.api_key):
        raise HTTPException(status_code=403, detail="Invalid API key")

    return api_key
