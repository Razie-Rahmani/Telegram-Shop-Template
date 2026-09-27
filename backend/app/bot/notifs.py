"""
Order-status customer notifications, and the single choke point for
"change status + notify" — shared by api/orders.py's PATCH endpoint and
bot/admin.py's confirm/reject/deliver buttons, so there's one place
responsible for messaging the customer regardless of which path triggered
the change.
"""
import json

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, BufferedInputFile

from .. import db
from ..config import ADMIN_ID
from .setup import bot

# All customer-facing text lives here — one file to translate/edit, instead
# of strings scattered across handlers.
STATUS_MESSAGES = {
    db.STATUS_PENDING_PAYMENT: "Your order has been placed and is awaiting payment.",
    db.STATUS_PENDING_CONFIRMATION: "Your payment receipt was received and is being reviewed.",
    db.STATUS_CONFIRMED: "Your payment is confirmed! Your order is being prepared.",
    db.STATUS_REJECTED: "Unfortunately your payment receipt could not be confirmed. Please contact us.",
    db.STATUS_DELIVERED: "Your order has been delivered. We hope you enjoy it!",
}


async def notify_customer_status(order: dict) -> None:
    customer_id = order.get("customer_telegram_id")
    if not customer_id:
        return
    message = STATUS_MESSAGES.get(order["status"], f"Your order status was updated: {order['status']}")
    try:
        await bot.send_message(int(customer_id), f"Order #{order['id']}\n\n{message}")
    except Exception as e:
        print(f"Customer status notification failed: {e}")


async def update_order_status_and_notify(order_id: int, status: str) -> dict | None:
    """Returns the updated order, or None if order_id doesn't exist — callers
    decide how to surface that (404 in the REST layer, a quiet alert in the
    bot)."""
    order = db.set_order_status(order_id, status)
    if order is None:
        return None
    await notify_customer_status(order)
    return order


def format_order_detail(order: dict) -> str:
    items = order["items"]
    if isinstance(items, str):
        items = json.loads(items)
    items_text = "\n".join(f"  - {name} x {qty}" for name, qty in items.items())
    return (
        f"Order #{order['id']} - {order['status']}\n\n"
        f"Customer: {order['customer_name']}\n"
        f"Phone: {order['phone_number']}\n"
        f"Address: {order['address']} ({order['postal_code']})\n"
        f"Telegram ID: {order['customer_telegram_id']}\n\n"
        f"Items:\n{items_text}\n\n"
        f"Total: {order['total_price']}"
    )


async def notify_admin_receipt(order: dict, contents: bytes, filename: str) -> None:
    caption = "New payment receipt\n\n" + format_order_detail(order)
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Confirm", callback_data=f"confirm_{order['id']}")],
            [InlineKeyboardButton(text="Reject", callback_data=f"reject_{order['id']}")],
        ]
    )
    try:
        photo = BufferedInputFile(contents, filename=filename)
        await bot.send_photo(ADMIN_ID, photo=photo, caption=caption, reply_markup=keyboard)
    except Exception as e:
        print(f"Admin receipt notification failed: {e}")