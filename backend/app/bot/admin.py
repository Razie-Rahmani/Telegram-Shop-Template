"""
Admin panel — entirely chat-driven, gated to a single Telegram user
(ADMIN_ID). No web form; every handler below double-checks the caller's ID
even though these buttons are only ever sent to the admin's own chat —
cheap defense in depth.

One shared FSM state (AdminStates.waiting_input) handles every "send me a
value" step across products/orders/FAQ/contact-info; `target` in FSM data
says which flow is in progress and what to do with the next message.
"""
from io import BytesIO

from aiogram import F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from .. import db
from ..config import ADMIN_ID, SHOP_NAME
from .setup import bot, dp
from .keyboards import (
    admin_menu_keyboard, order_list_keyboard, order_detail_keyboard,
    product_list_keyboard, product_detail_keyboard, faq_admin_list_keyboard,
)
from .notifs import update_order_status_and_notify, format_order_detail


class AdminStates(StatesGroup):
    waiting_input = State()


def _is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID


@dp.callback_query(F.data == "admin_back")
async def admin_back(callback: CallbackQuery, state: FSMContext):
    if not _is_admin(callback.from_user.id):
        await callback.answer("Not authorized.", show_alert=True)
        return
    await state.clear()
    await callback.message.answer(f"{SHOP_NAME} admin panel", reply_markup=admin_menu_keyboard())
    await callback.answer()


# --- Products ---

@dp.callback_query(F.data == "admin_products")
async def admin_products_menu(callback: CallbackQuery):
    if not _is_admin(callback.from_user.id):
        await callback.answer("Not authorized.", show_alert=True)
        return

    products = db.list_products()
    text = "Products — tap one to edit:" if products else "No products yet — add one below."
    await callback.message.answer(text, reply_markup=product_list_keyboard(products))
    await callback.answer()


@dp.callback_query(F.data.startswith("pview_"))
async def admin_product_detail(callback: CallbackQuery):
    if not _is_admin(callback.from_user.id):
        await callback.answer("Not authorized.", show_alert=True)
        return

    product_id = int(callback.data.split("_")[1])
    product = db.get_product(product_id)
    if not product:
        await callback.answer("Product not found.", show_alert=True)
        return

    photo_status = "has a photo" if product["has_image"] else "no photo yet"
    description = product["description"] or "(none)"
    text = (
        f"{product['name']}\n"
        f"Price: {product['price']}\n"
        f"Category: {product['category']}\n"
        f"Description: {description}\n"
        f"Photo: {photo_status}"
    )
    await callback.message.answer(text, reply_markup=product_detail_keyboard(product_id))
    await callback.answer()


@dp.callback_query(F.data.startswith("pedit_"))
async def admin_product_edit_prompt(callback: CallbackQuery, state: FSMContext):
    if not _is_admin(callback.from_user.id):
        await callback.answer("Not authorized.", show_alert=True)
        return

    _, field, product_id = callback.data.split("_")
    await state.update_data(product_id=int(product_id))

    if field == "photo":
        await state.set_state(AdminStates.waiting_input)
        await state.update_data(target="edit_photo")
        await callback.message.answer("Send the new photo:")
        await callback.answer()
        return

    prompts = {
        "name": "Send the new name:",
        "price": "Send the new price (numbers only):",
        "category": "Send the new category:",
        "description": "Send the new description (or \"skip\" to clear it):",
    }
    await state.set_state(AdminStates.waiting_input)
    await state.update_data(target=f"edit_{field}")
    await callback.message.answer(prompts[field])
    await callback.answer()


@dp.callback_query(F.data == "padd")
async def admin_add_product_start(callback: CallbackQuery, state: FSMContext):
    if not _is_admin(callback.from_user.id):
        await callback.answer("Not authorized.", show_alert=True)
        return

    await state.set_state(AdminStates.waiting_input)
    await state.update_data(target="add_name")
    await callback.message.answer("Send the new product's name:")
    await callback.answer()


# --- Orders ---

@dp.callback_query(F.data == "admin_orders")
async def admin_orders_menu(callback: CallbackQuery):
    if not _is_admin(callback.from_user.id):
        await callback.answer("Not authorized.", show_alert=True)
        return

    orders = db.list_orders(limit=20)
    if not orders:
        await callback.message.answer("No orders yet.", reply_markup=order_list_keyboard([]))
        await callback.answer()
        return

    await callback.message.answer("Last 20 orders:", reply_markup=order_list_keyboard(orders))
    await callback.answer()


@dp.callback_query(F.data.startswith("oview_"))
async def admin_order_detail(callback: CallbackQuery):
    if not _is_admin(callback.from_user.id):
        await callback.answer("Not authorized.", show_alert=True)
        return

    order_id = int(callback.data.split("_")[1])
    order = db.get_order(order_id)
    if not order:
        await callback.answer("Order not found.", show_alert=True)
        return

    await callback.message.answer(format_order_detail(order), reply_markup=order_detail_keyboard(order_id))
    await callback.answer()


@dp.callback_query(F.data.startswith("confirm_") | F.data.startswith("reject_") | F.data.startswith("deliver_"))
async def handle_decision(callback: CallbackQuery):
    if not _is_admin(callback.from_user.id):
        await callback.answer("Not authorized.", show_alert=True)
        return

    action, order_id = callback.data.split("_")
    status_map = {"confirm": db.STATUS_CONFIRMED, "reject": db.STATUS_REJECTED, "deliver": db.STATUS_DELIVERED}
    new_status = status_map[action]

    order = await update_order_status_and_notify(int(order_id), new_status)
    if order is None:
        await callback.answer("Order not found.", show_alert=True)
        return

    await callback.message.answer(f"Order #{order_id} {new_status}.")
    await callback.answer()


# --- FAQ ---

@dp.callback_query(F.data == "admin_faq")
async def admin_faq_menu(callback: CallbackQuery):
    if not _is_admin(callback.from_user.id):
        await callback.answer("Not authorized.", show_alert=True)
        return

    faqs = db.get_faqs()
    await callback.message.answer("FAQ — tap a question to edit its answer:", reply_markup=faq_admin_list_keyboard(faqs))
    await callback.answer()


@dp.callback_query(F.data.startswith("faqedit_"))
async def admin_faq_edit_prompt(callback: CallbackQuery, state: FSMContext):
    if not _is_admin(callback.from_user.id):
        await callback.answer("Not authorized.", show_alert=True)
        return

    key = callback.data.split("faqedit_")[1]
    faq = db.get_faq(key)
    if not faq:
        await callback.answer("FAQ entry not found.", show_alert=True)
        return

    await state.set_state(AdminStates.waiting_input)
    await state.update_data(target="faq_answer", faq_key=key)
    await callback.message.answer(f"Current answer:\n{faq['answer']}\n\nSend the new answer:")
    await callback.answer()


# --- Contact info ---

@dp.callback_query(F.data == "admin_contact")
async def admin_contact_prompt(callback: CallbackQuery, state: FSMContext):
    if not _is_admin(callback.from_user.id):
        await callback.answer("Not authorized.", show_alert=True)
        return

    current = db.get_contact_info() or "(not set)"
    await state.set_state(AdminStates.waiting_input)
    await state.update_data(target="contact_info")
    await callback.message.answer(f"Current contact info:\n{current}\n\nSend the new contact info:")
    await callback.answer()


# --- Shared text/photo-input handler for all of the flows above ---

@dp.message(AdminStates.waiting_input)
async def admin_text_input(message: Message, state: FSMContext):
    if not _is_admin(message.from_user.id):
        return

    data = await state.get_data()
    target = data.get("target")

    # --- Photo-accepting steps ---
    if target in ("add_photo", "edit_photo"):
        if target == "add_photo" and message.text and message.text.strip().lower() == "skip":
            image_bytes = None
        elif message.photo:
            await message.answer("Saving photo...")
            largest = message.photo[-1]
            buf = BytesIO()
            await bot.download(largest, destination=buf)
            image_bytes = buf.getvalue()
        else:
            prompt = "Please send a photo, or type \"skip\" to leave it without one." if target == "add_photo" else "Please send a photo."
            await message.answer(prompt)
            return

        if target == "add_photo":
            product_id = db.create_product(
                data["new_name"], data["new_price"], data["new_category"], data.get("new_description")
            )
            if image_bytes:
                db.save_product_image(product_id, image_bytes, "image/jpeg")
            summary = f"Added \"{data['new_name']}\" — {data['new_price']} ({data['new_category']})"
            summary += " with photo." if image_bytes else " (no photo)."
            await message.answer(summary, reply_markup=admin_menu_keyboard())
        else:  # edit_photo
            db.save_product_image(data["product_id"], image_bytes, "image/jpeg")
            await message.answer("Photo updated.", reply_markup=admin_menu_keyboard())

        await state.clear()
        return

    # --- Text-only steps ---
    value = (message.text or "").strip()
    if not value:
        await message.answer("Please send text.")
        return

    if target == "edit_name":
        db.update_product(data["product_id"], name=value)
        await message.answer("Name updated.", reply_markup=admin_menu_keyboard())
        await state.clear()

    elif target == "edit_price":
        if not value.isdigit():
            await message.answer("That doesn't look like a number — send the price again:")
            return
        db.update_product(data["product_id"], price=int(value))
        await message.answer("Price updated.", reply_markup=admin_menu_keyboard())
        await state.clear()

    elif target == "edit_category":
        db.update_product(data["product_id"], category=value)
        await message.answer("Category updated.", reply_markup=admin_menu_keyboard())
        await state.clear()

    elif target == "edit_description":
        new_description = None if value.lower() == "skip" else value
        db.update_product(data["product_id"], description=new_description)
        await message.answer("Description updated.", reply_markup=admin_menu_keyboard())
        await state.clear()

    elif target == "add_name":
        await state.update_data(new_name=value, target="add_price")
        await message.answer("Send the price (numbers only):")

    elif target == "add_price":
        if not value.isdigit():
            await message.answer("That doesn't look like a number — send the price again:")
            return
        await state.update_data(new_price=int(value), target="add_category")
        await message.answer("Send the category:")

    elif target == "add_category":
        await state.update_data(new_category=value, target="add_description")
        await message.answer("Send a description (or \"skip\" to leave it blank):")

    elif target == "add_description":
        new_description = None if value.lower() == "skip" else value
        await state.update_data(new_description=new_description, target="add_photo")
        await message.answer("Now send a photo of the product (or type \"skip\" to add it without one):")

    elif target == "faq_answer":
        db.update_faq_answer(data["faq_key"], value)
        await message.answer("FAQ answer updated.", reply_markup=admin_menu_keyboard())
        await state.clear()

    elif target == "contact_info":
        db.update_contact_info(value)
        await message.answer("Contact info updated.", reply_markup=admin_menu_keyboard())
        await state.clear()

    else:
        await state.clear()