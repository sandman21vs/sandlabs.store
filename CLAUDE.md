# CLAUDE.md

Claude-specific context for this repository. **`AGENTS.md` is the canonical
operating policy — defer to it for all shared rules** (language, architecture
safeguards, validation, delegation, git workflow, secrets). This file only adds
Claude Code shortcuts and orientation.

## What this project is

`sandlabs.store` — a Flask 3 + SQLite Bitcoin-settled e-commerce store.
Server-rendered Jinja templates with a client-side JS layer that renders
product cards from `window.PRODUTOS`. Payments settle in satoshis via Coinos
(Lightning / Liquid / on-chain). Customer PII is encrypted at rest.

## Layout

- `app.py` — app factory, blueprint registration, CSRF, security headers, `/health`.
- `config.py` — env-driven config. `db.py` — SQLite helper (WAL, FKs on).
- `init_db.py` — schema + idempotent migrations (run at startup).
- `i18n.py` + `translations/<lang>/*.json` — 4 languages: pt (default), en, es, de.
- `routes/routes_*.py` — blueprints (public, cart, auth, account, checkout, admin).
- `services/service_*.py` — business logic (pricing, btc_price, coinos, images, qr, security, shipping).
- `models/model_*.py` — raw-SQL data access.
- `templates/` — Jinja views. `static/` — css/js/images (served at root URLs).
- `tests/` — pytest suite. `scripts/` — seed_products, generate_thumbnails.

## Common commands

```bash
python -m pytest tests/ -q            # run the test suite
docker-compose up                     # run the app (host 8082 -> container 8000)
python scripts/generate_thumbnails.py # (re)build webp thumbnails
```

## Conventions

- Keep the `route -> service -> model` layering; route handlers stay thin.
- Add/adjust schema only via `init_db.py` idempotent migrations.
- All money in satoshis; fiat (CHF/USD/EUR/BRL) is converted at the edge.
- Never write PII to plaintext columns; never log decrypted PII.
- One focused commit per phase after tests pass; never commit to `main`.
