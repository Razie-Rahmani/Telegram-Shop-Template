"""
Bot/Dispatcher instances and the webhook wiring.

Everything else in bot/ (customer.py, admin.py, notifications.py) imports
`bot` and `dp` from here rather than creating its own — there must be
exactly one Bot and one Dispatcher for the whole app.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, APIRouter, Request
from aiogram import Bot, Dispatcher
from aiogram.types import Update
from aiogram.fsm.storage.memory import MemoryStorage

from ..config import BOT_TOKEN, WEBHOOK_PATH, WEBHOOK_URL, WEBHOOK_SECRET

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

router = APIRouter()


@router.post(WEBHOOK_PATH)
async def telegram_webhook(request: Request):
    if request.headers.get("X-Telegram-Bot-Api-Secret-Token") != WEBHOOK_SECRET:
        return {"ok": False}, 401

    data = await request.json()
    update = Update.model_validate(data, context={"bot": bot})
    await dp.feed_update(bot, update)
    return {"ok": True}


@asynccontextmanager
async def lifespan(app: FastAPI):
    await bot.set_webhook(
        url=WEBHOOK_URL,
        secret_token=WEBHOOK_SECRET,
        drop_pending_updates=True,
    )
    yield
    await bot.session.close()