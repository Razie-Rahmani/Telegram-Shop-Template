"""
Central configuration. Every environment variable the app touches is read
exactly once, here — nothing else in the app should call os.getenv directly.
This keeps .env.example trivially in sync with what's actually used, and
means a missing var fails loudly at import time instead of deep in a handler.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# One .env file, at the project root (not backend/.env), so there's a single
# place to look for every variable regardless of which shop this template
# becomes. Path is computed relative to this file, not the current working
# directory, so it loads correctly whether you run the app from the repo
# root, from backend/, or via an ASGI server started elsewhere.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(_PROJECT_ROOT / ".env")

# --- Telegram bot ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0")) or None  # None until set — see startup check below

# --- Webhook ---
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")

# --- Database ---
DATABASE_URL = os.getenv("DATABASE_URL")

# --- Admin REST auth ---
# Gates the write/admin REST endpoints (add/edit product, list orders, change
# status) from anonymous access. The bot's own admin flows call the shared
# db.py functions directly in-process, so they never go through this check —
# it only gates real HTTP requests (curl, Postman, browser, etc).
ADMIN_API_TOKEN = os.getenv("ADMIN_API_TOKEN")

# --- Shop identity ---
# Template pulls both out so a new shop is a .env edit, not a code edit.
SHOP_NAME = os.getenv("SHOP_NAME", "My Shop")
SHOP_FRONTEND_URL = os.getenv("SHOP_FRONTEND_URL")

# --- Startup sanity checks ---
# Fail fast and clearly at boot rather than with a cryptic error on first
# request. Doesn't replace testing — just turns "forgot to set ADMIN_ID"
# into an obvious message instead of a silent None comparison later.
_REQUIRED = {
    "BOT_TOKEN": BOT_TOKEN,
    "ADMIN_ID": ADMIN_ID,
    "WEBHOOK_URL": WEBHOOK_URL,
    "WEBHOOK_SECRET": WEBHOOK_SECRET,
    "DATABASE_URL": DATABASE_URL,
    "ADMIN_API_TOKEN": ADMIN_API_TOKEN,
    "SHOP_FRONTEND_URL": SHOP_FRONTEND_URL,
}


def check_required_env() -> None:
    missing = [name for name, value in _REQUIRED.items() if not value]
    if missing:
        raise RuntimeError(
            f"Missing required environment variable(s): {', '.join(missing)}. "
            f"Copy .env.example to .env and fill these in."
        )