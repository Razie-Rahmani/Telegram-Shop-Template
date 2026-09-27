"""
Postgres connection, schema, and every query in the app.

Both api/ (REST) and bot/ (aiogram admin flows) call into this module
directly rather than one importing from the other — avoids the circular
import Bloomika's main.py sidestepped only by having everything in one file.
"""

import psycopg2
import psycopg2.extras
import json

from .config import DATABASE_URL

# --- Order status values ---
# Bloomika used "pending payment" (space) alongside "pending_confirmation"
# (underscore) — a known inconsistency flagged as a trap for future
# `WHERE status = ...` queries. Template uses underscores throughout.
STATUS_PENDING_PAYMENT = "pending_payment"
STATUS_PENDING_CONFIRMATION = "pending_confirmation"
STATUS_CONFIRMED = "confirmed"
STATUS_REJECTED = "rejected"
STATUS_DELIVERED = "delivered"


def get_connection():
    return psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)


def init_db() -> None:
    """Safe to run on every boot — only creates tables/seeds rows that don't
    already exist."""
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS products(
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            price INTEGER NOT NULL,
            category TEXT NOT NULL,
            image_data BYTEA,
            image_mimetype TEXT
        )
    """)
    cur.execute("ALTER TABLE products ADD COLUMN IF NOT EXISTS image_data BYTEA")
    cur.execute("ALTER TABLE products ADD COLUMN IF NOT EXISTS image_mimetype TEXT")
    cur.execute("ALTER TABLE products ADD COLUMN IF NOT EXISTS description TEXT")

    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS orders(
            id SERIAL PRIMARY KEY,
            customer_telegram_id TEXT,
            customer_name TEXT NOT NULL,
            phone_number TEXT,
            postal_code TEXT NOT NULL,
            address TEXT NOT NULL,
            items TEXT NOT NULL,
            total_price INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT '{STATUS_PENDING_PAYMENT}'
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS faq(
            key TEXT PRIMARY KEY,
            question TEXT NOT NULL,
            answer TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS contact_info(
            id SERIAL PRIMARY KEY,
            content TEXT NOT NULL
        )
    """)
    conn.commit()

    cur.execute("SELECT COUNT(*) AS count FROM contact_info")
    if cur.fetchone()["count"] == 0:
        cur.execute(
            "INSERT INTO contact_info (content) VALUES (%s)",
            ("Phone: 0000000000\nInstagram: instagram.com/your_shop\nHours: every day, 9am-9pm",)
        )
        conn.commit()

    cur.execute("SELECT COUNT(*) AS count FROM faq")
    if cur.fetchone()["count"] == 0:
        defaults = [
            ("faq_availability", "Is it available?", "Yes, in-stock items are shown in the Mini App."),
            ("faq_price", "What's the price?", "Prices are listed inside the Mini App."),
            ("faq_delivery", "Do you deliver?", "Yes, we deliver."),
        ]
        cur.executemany(
            "INSERT INTO faq (key, question, answer) VALUES (%s, %s, %s)",
            defaults
        )
        conn.commit()

    cur.close()
    conn.close()


# --- Products ---

def list_products():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, name, description, price, category, (image_data IS NOT NULL) AS has_image FROM products ORDER BY id"
    )
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def get_product(product_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, name, description, price, category, (image_data IS NOT NULL) AS has_image FROM products WHERE id = %s",
        (product_id,)
    )
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def create_product(name: str, price: int, category: str, description: str | None = None) -> int:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO products (name, description, price, category) VALUES (%s, %s, %s, %s) RETURNING id",
        (name, description, price, category)
    )
    conn.commit()
    product_id = cur.fetchone()["id"]
    conn.close()
    return product_id


def update_product(product_id: int, **fields):
    """fields: any of name, description, price, category — only non-None
    values are applied."""
    set_clauses, values = [], []
    for col in ("name", "description", "price", "category"):
        if fields.get(col) is not None:
            set_clauses.append(f"{col} = %s")
            values.append(fields[col])
    if not set_clauses:
        return get_product(product_id)

    conn = get_connection()
    cur = conn.cursor()
    values.append(product_id)
    cur.execute(f"UPDATE products SET {', '.join(set_clauses)} WHERE id = %s", values)
    conn.commit()
    conn.close()
    return get_product(product_id)


def save_product_image(product_id: int, data: bytes, mimetype: str) -> None:
    """Stored directly in Postgres — avoids a third-party CDN dependency
    (relevant if a deployment target has unreliable CDN access)."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE products SET image_data = %s, image_mimetype = %s WHERE id = %s",
        (psycopg2.Binary(data), mimetype, product_id)
    )
    conn.commit()
    conn.close()


def get_product_image(product_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT image_data, image_mimetype FROM products WHERE id = %s", (product_id,))
    row = cur.fetchone()
    conn.close()
    if not row or row["image_data"] is None:
        return None
    return bytes(row["image_data"]), row["image_mimetype"] or "image/jpeg"


# --- Orders ---

def create_order(customer_telegram_id: str, customer_name: str, address: str,
                  phone_number: str, postal_code: str, items: dict, total_price: int) -> int:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO orders (customer_telegram_id, customer_name, address, phone_number,
                             postal_code, items, total_price, status)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
        """,
        (customer_telegram_id, customer_name, address, phone_number, postal_code,
         json.dumps(items), total_price, STATUS_PENDING_PAYMENT)
    )
    conn.commit()
    order_id = cur.fetchone()["id"]
    conn.close()
    return order_id


def _deserialize_order(row: dict) -> dict:
    order = dict(row)
    if isinstance(order.get("items"), str):
        order["items"] = json.loads(order["items"])
    return order


def list_orders(limit: int | None = None):
    conn = get_connection()
    cur = conn.cursor()
    if limit:
        cur.execute("SELECT * FROM orders ORDER BY id DESC LIMIT %s", (limit,))
    else:
        cur.execute("SELECT * FROM orders ORDER BY id DESC")
    rows = cur.fetchall()
    conn.close()
    return [_deserialize_order(r) for r in rows]


def get_order(order_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM orders WHERE id = %s", (order_id,))
    row = cur.fetchone()
    conn.close()
    return _deserialize_order(row) if row else None


def get_latest_pending_payment_order(customer_telegram_id: str):
    """Used by the receipt-photo handler to match an incoming photo back to
    the customer's most recent unpaid order."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM orders WHERE customer_telegram_id = %s AND status = %s ORDER BY id DESC LIMIT 1",
        (customer_telegram_id, STATUS_PENDING_PAYMENT)
    )
    row = cur.fetchone()
    conn.close()
    return _deserialize_order(row) if row else None


def set_order_status(order_id: int, status: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE orders SET status = %s WHERE id = %s", (status, order_id))
    conn.commit()
    conn.close()
    return get_order(order_id)


# --- FAQ ---

def get_faqs():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM faq ORDER BY key")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def get_faq(key: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM faq WHERE key = %s", (key,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def update_faq_answer(key: str, answer: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE faq SET answer = %s WHERE key = %s", (answer, key))
    conn.commit()
    cur.execute("SELECT * FROM faq WHERE key = %s", (key,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


# --- Contact info ---

def get_contact_info():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT content FROM contact_info ORDER BY id LIMIT 1")
    row = cur.fetchone()
    conn.close()
    return row["content"] if row else None


def update_contact_info(content: str):
    """Not present in Bloomika's shipped code (README describes it, code
    didn't implement it) — added here for parity with FAQ editing."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM contact_info ORDER BY id LIMIT 1")
    row = cur.fetchone()
    if row:
        cur.execute("UPDATE contact_info SET content = %s WHERE id = %s", (content, row["id"]))
    else:
        cur.execute("INSERT INTO contact_info (content) VALUES (%s)", (content,))
    conn.commit()
    conn.close()
    return get_contact_info()