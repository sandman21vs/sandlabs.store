# sandlabs.store

An open-source store for Bitcoin hardware that settles every order in Bitcoin.
Fork it to run your own shop.

- **Stack:** Python 3.12, Flask 3, SQLite, Jinja templates, vanilla JS and CSS
  (no build step).
- **Payments:** Lightning, Liquid and on-chain through
  [Coinos](https://coinos.io). All amounts are handled in satoshis; fiat
  (CHF / USD / EUR / BRL) is only a display and pricing input.
- **Shipping:** Swiss Post rate table with optional live carrier integrations.
- **Privacy:** customer names, addresses and emails are encrypted at rest.
- **Languages:** Portuguese (default), English, Spanish and German.

`ARCHITECTURE.md` has the detailed design. `AGENTS.md` has the contribution
rules for people and AI agents.

## Features

- Product catalog with image galleries, WebP thumbnails and a zoom lightbox.
- Cart for anonymous sessions and logged-in customers.
- Checkout with or without an account; guest orders are tracked with an order
  number plus access token at `/orders/lookup`.
- Per-order invoice or address with QR code, payment polling and a Coinos
  webhook.
- PDF receipt with a tracking QR code.
- Server-side discount coupons.
- Admin panel: products, orders, tracking codes, coupons, shipping rates and
  integration settings.

## Run it

### Docker

```bash
cp .env.example .env      # then edit SECRET_KEY and MASTER_MNEMONIC
docker-compose up --build
```

The store listens on <http://localhost:8082>. The SQLite database is kept in
`./data`, which is mounted into the container.

On first start, open `/admin/setup` to create the admin account and enter the
Coinos credentials. Leave `ADMIN_PASSWORD` empty in `.env` to use this wizard.

### Local Python

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt -r requirements-dev.txt
.venv/bin/python scripts/seed_products.py   # optional: sample catalog
.venv/bin/python app.py                     # http://localhost:8000 (debug)
```

Production runs on Python 3.12. On newer interpreters the pinned `Pillow` may
have no wheel; install the same packages with an unpinned `pillow` instead.

## Configuration

Environment variables (see `.env.example`):

| Variable | Purpose |
|---|---|
| `SECRET_KEY` | Flask session signing key. Required. |
| `MASTER_MNEMONIC` | BIP39 phrase that derives the PII encryption keys. Required in production. Back it up; without it stored customer data cannot be decrypted. |
| `MASTER_MNEMONIC_PASSPHRASE` | Optional passphrase for the mnemonic. |
| `SHIPPING_DATA_KEY` | Legacy encryption key, kept only to decrypt old data. |
| `DATABASE_PATH` | SQLite file path. Defaults to `data/sandlabs.db`. |
| `ADMIN_USERNAME`, `ADMIN_PASSWORD` | Optional admin bootstrap; otherwise use `/admin/setup`. |
| `COINOS_API_KEY`, `COINOS_WEBHOOK_SECRET`, `COINOS_ENABLED` | Bootstrap defaults for Coinos. Values saved in `/admin/settings` take priority. |
| `PUBLIC_BASE_URL` | Canonical HTTPS origin used in receipt QR codes. |
| `STORE_WHATSAPP`, `STORE_TELEGRAM` | Fallback contact handles when not set in the admin. |
| `FLASK_ENV=production` | Makes the app refuse to start without a dedicated PII secret. |

Everything else (contacts, payment methods, shipping rates, carrier
credentials, coupons) is managed in the admin panel and stored in SQLite.

## Tests

```bash
.venv/bin/python -m pytest tests/ -q
```

The same command runs in CI on every pull request.

## Project layout

```
app.py              App factory, CSRF, security headers, /health
config.py           Environment-driven configuration
db.py               SQLite connection helper
init_db.py          Schema and idempotent migrations (run at startup)
i18n.py             Language detection and translation lookup
routes/             Flask blueprints: public, cart, auth, account, checkout, admin
services/           Business logic: pricing, BTC rates, Coinos, shipping, images, PDF, QR, encryption
models/             Raw-SQL data access
templates/          Jinja views
static/             CSS, JavaScript and images (served from the site root)
translations/       pt, en, es, de message catalogs
scripts/            seed_products.py, generate_thumbnails.py
tests/              pytest suite
docs/ROADMAP.md     Active plan
docs/archive/       Finished plans and briefs
```

Requests flow `route -> service -> model`. Route handlers stay thin and
services do not import Flask.

## Making it your own

- **Catalog:** manage products, prices, images and options in `/admin`.
  `scripts/seed_products.py` shows the data shape.
- **Contacts and integrations:** `/admin/settings`.
- **Look and feel:** design tokens at the top of `static/css/style.css`.
- **Copy:** `translations/<lang>/*.json`.
- **Branding:** replace `static/images/logo.png`. Before publishing a fork,
  remove the Sandlabs name, logo and contacts so customers are not misled about
  who runs your shop.

## Deployment notes

- Run behind an HTTPS reverse proxy or tunnel; the app sends HSTS outside debug
  mode.
- Persist and back up the `data/` directory and the `MASTER_MNEMONIC`.
- Point the Coinos webhook at `/checkout/webhook/coinos`.
- `GET /health` returns `{"status": "ok"}` for health checks.

## Contributing

Changes land through pull requests; see `AGENTS.md` for the workflow and the
definition of done.

## License

GPLv3.
