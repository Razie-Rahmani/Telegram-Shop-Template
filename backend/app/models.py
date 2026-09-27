"""Pydantic models for the REST API's request/response bodies."""
from pydantic import BaseModel
from typing import Optional


class Product(BaseModel):
    name: str
    price: int
    category: str
    description: Optional[str] = None


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    price: Optional[int] = None
    category: Optional[str] = None
    description: Optional[str] = None


class Order(BaseModel):
    customer_telegram_id: str
    customer_name: str
    address: str
    postal_code: str
    phone_number: str
    items: dict
    total_price: int


class StatusUpdate(BaseModel):
    status: str