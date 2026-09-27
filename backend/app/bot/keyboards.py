"""
Every InlineKeyboardMarkup the bot sends, in one place.

Bloomika built these inline at each call site, often repeating the same
button shape (Confirm/Reject, a Back button) across multiple handlers.
Centralizing them here means a button's text or callback_data only needs
to change in one place.
"""
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

from ..config import SHOP_FRONTEND_URL

BACK_BUTTON = InlineKeyboardButton(text="Back", callback_data="admin_back")


def admin_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Edit Products", callback_data="admin_products")],
        [InlineKeyboardButton(text="View Orders", callback_data="admin_orders")],
        [InlineKeyboardButton(text="Edit FAQ", callback_data="admin_faq")],
        [InlineKeyboardButton(text="Edit Contact Info", callback_data="admin_contact")],
    ])


def customer_main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="FAQ", callback_data="faq_menu")],
        [InlineKeyboardButton(text="Contact Us", callback_data="contact_us")],
        [InlineKeyboardButton(text="Open Shop", web_app=WebAppInfo(url=SHOP_FRONTEND_URL))],
    ])


def faq_menu_keyboard(faqs: list[dict]) -> InlineKeyboardMarkup:
    """Built from whatever's actually in the faq table, so a new/renamed FAQ
    entry shows up here automatically. Bloomika's customer-facing FAQ menu
    was a hardcoded 3-button list that could drift from the FAQ table the
    admin panel actually edits — this keeps the two in sync by construction."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f["question"], callback_data=f["key"])]
        for f in faqs
    ])


def order_list_keyboard(orders: list[dict]) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text=f"#{o['id']} - {o['customer_name']} ({o['status']})", callback_data=f"oview_{o['id']}")]
        for o in orders
    ]
    buttons.append([BACK_BUTTON])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def order_detail_keyboard(order_id: int, include_deliver: bool = True) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="Confirm", callback_data=f"confirm_{order_id}")],
        [InlineKeyboardButton(text="Reject", callback_data=f"reject_{order_id}")],
    ]
    if include_deliver:
        buttons.append([InlineKeyboardButton(text="Mark Delivered", callback_data=f"deliver_{order_id}")])
    buttons.append([InlineKeyboardButton(text="Back", callback_data="admin_orders")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def product_list_keyboard(products: list[dict]) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text=f"{p['name']} - {p['price']}", callback_data=f"pview_{p['id']}")]
        for p in products
    ]
    buttons.append([InlineKeyboardButton(text="Add New Product", callback_data="padd")])
    buttons.append([BACK_BUTTON])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def product_detail_keyboard(product_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Name", callback_data=f"pedit_name_{product_id}")],
        [InlineKeyboardButton(text="Price", callback_data=f"pedit_price_{product_id}")],
        [InlineKeyboardButton(text="Category", callback_data=f"pedit_category_{product_id}")],
        [InlineKeyboardButton(text="Description", callback_data=f"pedit_description_{product_id}")],
        [InlineKeyboardButton(text="Photo", callback_data=f"pedit_photo_{product_id}")],
        [InlineKeyboardButton(text="Back", callback_data="admin_products")],
    ])


def faq_admin_list_keyboard(faqs: list[dict]) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text=f["question"], callback_data=f"faqedit_{f['key']}")]
        for f in faqs
    ]
    buttons.append([BACK_BUTTON])
    return InlineKeyboardMarkup(inline_keyboard=buttons)