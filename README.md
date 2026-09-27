# Telegram Mini App Shop — Template

A reusable starting point for Telegram Mini App shops: a FastAPI backend that
runs both a REST API and an aiogram Telegram bot in one process, a vanilla
HTML/JS/CSS Mini App frontend, and a fully chat-driven admin panel — no
separate admin website needed.

Extracted from a production flower-shop bot and generalized for reuse.

## Features

- **Product catalog** — browse, add to cart, and check out inside the
  Telegram Mini App, backed by a REST API.
- **Order flow with a real state machine** — `pending_payment` →
  `pending_confirmation` → `confirmed` / `rejected` → `delivered`, with a
  single function responsible for every status change and its customer
  notification.
- **Chat-driven admin panel** — the shop owner manages products, orders,
  FAQ, and contact info entirely through Telegram messages and buttons. No
  admin website, no separate login system.
- **Receipt-by-photo payment confirmation** — customers send their payment
  receipt as a Telegram photo directly to the bot (proven more reliable
  than in-Mini-App uploads across proxies and WebViews), matched
  automatically to their most recent unpaid order.
- **Config-driven, not code-driven** — starting a new shop from this
  template is an `.env` edit and a `SHOP_CONFIG` edit, not a code change.
- **Restyle in one file** — every color, font, and spacing value in the
  frontend is a CSS variable in `style.css`. `index.html` and `app.js`
  contain no visual decisions at all.

## Tech stack

| Layer       | Technology                                   |
|-------------|-----------------------------------------------|
| Backend     | Python, FastAPI, aiogram 3                    |
| Database    | PostgreSQL (`psycopg2`)                       |
| Frontend    | Vanilla HTML / CSS / JavaScript — no build step |
| Bot/API     | Single process — one FastAPI app serves both the REST API and the Telegram webhook |

## Project structure

```
telegram-shop-template/
├── .env.example              # every env var the app needs — copy to .env and fill in
├── backend/
│   ├── requirements.txt
│   └── app/
│       ├── main.py           # entrypoint — composes everything below
│       ├── config.py         # all env vars, read once
│       ├── db.py             # Postgres connection, schema, every query
│       ├── models.py         # Pydantic request/response models
│       ├── deps.py           # admin REST auth dependency
│       ├── api/
│       │   ├── products.py   # product catalog REST endpoints
│       │   └── orders.py     # order REST endpoints
│       └── bot/
│           ├── setup.py         # Bot/Dispatcher instances, webhook route
│           ├── keyboards.py     # every inline keyboard, centralized
│           ├── customer.py      # /start, FAQ, contact us, receipt intake
│           ├── admin.py         # chat-driven admin panel
│           └── notifications.py # customer notifications, status+notify choke point
└── frontend/
    ├── index.html             # structure + SHOP_CONFIG block
    ├── app.js                 # catalog/cart/checkout logic — no visual decisions
    └── style.css              # every visual decision, as CSS variables
```

## Prerequisites

- Python 3.11+
- A PostgreSQL database (e.g. a free instance from [Neon](https://neon.tech)
  or [Render](https://render.com))
- A Telegram bot token from [@BotFather](https://t.me/BotFather)
- Your own numeric Telegram user ID from [@userinfobot](https://t.me/userinfobot)
  (this becomes the admin account)

## Getting started

1. **Clone and enter the project.**

   ```bash
   git clone <this-repo-url> my-new-shop
   cd my-new-shop
   ```

2. **Create your `.env` file.**

   ```bash
   cp .env.example .env
   ```

   Open `.env` and fill in every value — see [Environment
   variables](#environment-variables) below for what each one means.

3. **Install backend dependencies.**

   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate      # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

4. **Configure the frontend.**

   Open `frontend/index.html` and edit the `window.SHOP_CONFIG` block near
   the top — at minimum, set `apiBase` to your deployed backend's URL.

5. **Run the backend.**

   ```bash
   uvicorn app.main:app --reload
   ```

   On startup the app validates that every required env var is set and
   creates any missing database tables automatically — safe to run on every
   boot.

6. **Serve the frontend** anywhere that serves static files (GitHub Pages,
   Render static site, Netlify, etc.), then set that URL as
   `SHOP_FRONTEND_URL` in `.env` and `apiBase` in `SHOP_CONFIG`.

> **Local development note:** Telegram delivers bot updates via webhook to
> a public HTTPS URL — `localhost` won't work. For local testing, tunnel
> your local server with a tool like [ngrok](https://ngrok.com) and point
> `WEBHOOK_URL` at the tunnel's URL.

## Environment variables

All of these live in `.env` at the project root (see `.env.example`).

| Variable            | Description                                                            |
|---------------------|--------------------------------------------------------------------------|
| `BOT_TOKEN`         | From @BotFather.                                                        |
| `ADMIN_ID`           | Your numeric Telegram user ID — this account gets admin panel access.  |
| `WEBHOOK_URL`        | Public URL Telegram sends updates to, e.g. `https://your-app.onrender.com/webhook`. |
| `WEBHOOK_SECRET`     | Any random string you choose — verified on every incoming webhook request. |
| `DATABASE_URL`       | Full Postgres connection string.                                        |
| `ADMIN_API_TOKEN`    | Any random string — required in the `X-Admin-Token` header on admin REST endpoints. |
| `SHOP_NAME`          | Shown in the bot's welcome message and admin panel header.              |
| `SHOP_FRONTEND_URL`  | URL of the deployed Mini App frontend, opened via the bot's "Open Shop" button. |

## Deployment

The backend and frontend deploy as two separate services — this is how the
original shop this template was extracted from runs in production:

- **Backend**: any host that runs a long-lived Python process (Render,
  Railway, Fly.io, etc.). Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
- **Frontend**: any static file host (Render static site, Netlify, GitHub
  Pages). No build step required — it's plain HTML/CSS/JS.
- **Database**: a managed Postgres instance (Neon, Render Postgres, etc.).
  Point `DATABASE_URL` at it.

After deploying the backend, set `WEBHOOK_URL` to its public `/webhook`
URL and redeploy — the app registers the webhook with Telegram on every
startup.

## Starting a new shop from this template

1. Copy this repository to a new project.
2. Fill in `.env` with the new shop's bot token, admin ID, database, and
   secrets.
3. Edit `SHOP_CONFIG` in `frontend/index.html` — name, API URL, currency,
   payment details.
4. Restyle `style.css` — this is the one file that defines the shop's
   look. Hand it to an AI with a style prompt, or edit the `:root`
   variables directly. No changes to `index.html` or `app.js` are needed
   for a restyle.
5. Deploy backend + frontend, point the webhook at the new backend, and
   the new shop is live.

No application code needs to change for a new shop — only config and
styling.

## Architecture notes

A few patterns worth understanding before extending this template:

- **Single status-change choke point.** `bot/notifications.py`'s
  `update_order_status_and_notify()` is the only place an order's status
  changes and a customer gets notified — called by both the REST API
  (`PATCH /orders/{id}`) and the bot's admin confirm/reject/deliver
  buttons. Change status any other way and the customer won't be notified.
- **Receipts come in via bot chat, not REST upload.** Large or flaky
  uploads through Mini App WebViews were unreliable in practice; sending
  the receipt as a normal Telegram photo message reuses Telegram's own
  reliable file transport instead.
- **`api/` and `bot/` never import each other's route/handler code** —
  only shared logic in `db.py` and `bot/notifications.py`. This avoids
  circular imports while still letting REST calls and bot button presses
  trigger the same underlying behavior.
- **Frontend config, structure, and style are fully separated** across
  `index.html`'s `SHOP_CONFIG` block, `app.js`, and `style.css`
  respectively — each can be edited independently without touching the
  others.

## License

Add your preferred license here (MIT is a common default for a personal
template like this).