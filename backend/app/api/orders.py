"""Order REST endpoints — create, list, and change status."""
from fastapi import APIRouter, Depends, HTTPException

from ..models import Order, StatusUpdate
from ..deps import verify_admin_token
from .. import db
from ..bot.notifs import update_order_status_and_notify

router = APIRouter()


@router.post("/orders/")
def create_order(order: Order):
    order_id = db.create_order(
        order.customer_telegram_id, order.customer_name, order.address,
        order.phone_number, order.postal_code, order.items, order.total_price
    )
    return {
        "order_id": order_id,
        "status": db.STATUS_PENDING_PAYMENT,
        "items": order.items,
        "total_price": order.total_price,
    }


@router.get("/orders", dependencies=[Depends(verify_admin_token)])
def list_orders():
    return db.list_orders()


@router.patch("/orders/{order_id}", dependencies=[Depends(verify_admin_token)])
async def update_status(order_id: int, update: StatusUpdate):
    order = await update_order_status_and_notify(order_id, update.status)
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    return order