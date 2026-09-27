"""
Entrypoint. Deliberately thin — everything with actual logic lives in
config/db/models/api/bot; this file just composes them.

Run with: uvicorn app.main:app  (from the backend/ directory)
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import check_required_env
from .db import init_db
from .bot.setup import lifespan, router as webhook_router

# Imported for their side effect: each of these modules registers its
# handlers on the shared `dp` (from bot.setup) via @dp.message /
# @dp.callback_query decorators at import time. Nothing here calls into
# them directly — if either import is removed, the bot silently stops
# responding to that category of update.
from .bot import customer, admin  # noqa: F401

from .api.products import router as products_router
from .api.orders import router as orders_router

check_required_env()  # fail loudly at boot if a required env var is missing
init_db()              # safe to run every boot — only creates what's missing

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(webhook_router)
app.include_router(products_router)
app.include_router(orders_router)