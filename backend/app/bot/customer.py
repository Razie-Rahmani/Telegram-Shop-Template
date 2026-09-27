"""
Customer-facing bot handlers.

/start branches into either the customer welcome menu or the admin panel
based on ADMIN_ID. The admin branch here just shows the
keyboard; the actual admin flows live in admin.py.
"""
from io import BytesIO

from aiogram import F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery

from .. import db
from ..config import ADMIN_ID, SHOP_NAME
from .setup import bot, dp
from .keyboards import admin_menu_keyboard, customer_main_menu_keyboard, faq_menu_keyboard
from .notifs import notify_admin_receipt, update_order_status_and_notify


@dp.message(Command("start"))
async def start(message: Message):
    if message.from_user.id == ADMIN_ID:
        await message.answer(f"{SHOP_NAME} admin panel", reply_markup=admin_menu_keyboard())
        return

    text = f"Welcome to {SHOP_NAME}! Open the shop to browse and order."
    await message.answer(text, reply_markup=customer_main_menu_keyboard())


@dp.callback_query(F.data == "faq_menu")
async def show_faq_menu(callback: CallbackQuery):
    faqs = db.get_faqs()
    await callback.message.answer("Choose a question:", reply_markup=faq_menu_keyboard(faqs))
    await callback.answer()


@dp.callback_query(F.data.startswith("faq_") & ~F.data.contains("menu"))
async def answer_faq(callback: CallbackQuery):
    faq = db.get_faq(callback.data)
    answer = faq["answer"] if faq else "Sorry, no answer is set for this question yet."
    await callback.message.answer(answer)
    await callback.answer()


@dp.callback_query(F.data == "contact_us")
async def show_contact_us(callback: CallbackQuery):
    text = db.get_contact_info() or "Contact info hasn't been set yet."
    await callback.message.answer(text)
    await callback.answer()


# ============================================================
# Receipt intake. Receipts come in as a normal Telegram photo message to
# the bot (not a REST upload) — large uploads were silently dropped at the
# platform/proxy level before reaching the backend, and small uploads were
# flaky specifically inside Telegram's iOS Mini App WebView. Neither is
# fixable from application code, so this reuses the same bot.download()
# mechanism already used for product photos, which is proven reliable.
#
# Tradeoff: only works for customers who opened the shop through the bot
# (so customer_telegram_id is populated) — opening the frontend URL
# directly in a browser is not a supported path for payment.
# ============================================================

@dp.message(F.photo, F.from_user.id != ADMIN_ID)
async def customer_receipt_photo(message: Message):
    order = db.get_latest_pending_payment_order(str(message.from_user.id))
    if not order:
        await message.answer(
            "No order found to attach a receipt to. Please place an order first, then send the receipt."
        )
        return

    largest = message.photo[-1]
    buf = BytesIO()
    await bot.download(largest, destination=buf)
    contents = buf.getvalue()

    order = await update_order_status_and_notify(order["id"], db.STATUS_PENDING_CONFIRMATION)

    await notify_admin_receipt(order, contents, f"receipt_{order['id']}.jpg")