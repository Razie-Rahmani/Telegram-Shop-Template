"""
Admin REST auth. Gates write/admin REST endpoints from anonymous access.

The bot's own admin flows (bot/admin.py) call db.py functions directly and
never go through this — it only checks real HTTP requests.
"""
from fastapi import HTTPException, Header

from .config import ADMIN_API_TOKEN


def verify_admin_token(x_admin_token: str = Header(None)):
    if not ADMIN_API_TOKEN:
        # Fail closed: if no token is configured, admin endpoints are
        # unreachable rather than silently wide open.
        raise HTTPException(status_code=503, detail="Admin auth not configured")
    if x_admin_token != ADMIN_API_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")