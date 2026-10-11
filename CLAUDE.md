# CLAUDE.md

Claude-specific context for this repository. **`AGENTS.md` is the canonical
operating policy — defer to it for all shared rules** (pull-request workflow,
language, architecture safeguards, validation, delegation, secrets). This file
only adds orientation and shortcuts.

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
- `docs/ROADMAP.md` — the active plan. `docs/archive/` — finished plans (history only).

## Common commands

The pinned `Pillow` has no wheel for very new local Pythons; if
`pip install -r requirements.txt` fails, install the same packages with an
unpinned `pillow` into the gitignored `.venv`.

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt -r requirements-dev.txt
.venv/bin/python -m pytest tests/ -q      # run the test suite
docker-compose up                         # run the app (host 8082 -> container 8000)
.venv/bin/python scripts/generate_thumbnails.py   # (re)build webp thumbnails
```

## Workflow in one paragraph

Work from the approved plan in `docs/ROADMAP.md`: one branch and one pull
request per phase, tests green before every push, never commit to or merge
into `main`, and no AI attribution in commits or pull requests. See
`AGENTS.md` for the full rules.
