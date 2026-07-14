# sandlabs.store Contributor and AI Operating Rules

This file is the canonical operating policy for everyone contributing to this
repository, including AI agents. `CLAUDE.md` provides Claude-specific context
and defers to this document for all shared rules.

`sandlabs.store` is a Flask 3 + SQLite e-commerce app that sells hardware and
settles payments in Bitcoin (Lightning / Liquid / on-chain) through Coinos.
Data lives in SQLite (`data/sandlabs.db`); there is no ORM and no frontend
build step.

## Language and documentation

- Communicate with each user in their preferred language, and follow an
  explicitly stated change of preference.
- Write repository code, comments, commit messages, pull requests, and
  technical documentation in English.
- Keep the product intentionally multilingual. The store ships **four**
  languages: `pt` (default), `en`, `es`, and `de` (see `SUPPORTED_LANGS` in
  `i18n.py`). `translations/<lang>/*.json` and any user-facing PT/EN/ES/DE copy
  are exceptions to the English technical-language rule.
- Update `README.md` and `ARCHITECTURE.md` (and any security documentation)
  whenever a change affects setup, deployment, security, integrations, routes,
  or persisted-data behavior.

## Architecture and product safeguards

- Follow the existing layering: route handlers (`routes/routes_*.py`) delegate
  to services (`services/service_*.py`), and services use the model/data layer
  (`models/model_*.py`). Keep route handlers thin. Services must not import
  Flask (the one allowed exception is `service_qr.py`, which uses `send_file`).
- Preserve CSRF protection (global in `app.py`; only the Coinos webhook is
  exempt), `login_required` / `admin_required` boundaries, i18n detection and
  fallbacks (`i18n.py`), HTML sanitization, and financial/accounting behavior
  (all money is handled in satoshis end-to-end).
- Treat Coinos credentials, wallet addresses, payment webhooks, invoice
  hashes, balances, the PII encryption key/seed, and encrypted customer data
  as security-sensitive. Coinos logic lives in `services/service_coinos.py`;
  at-rest encryption lives in `services/service_security.py`. Do not weaken
  their validation, authorization, audit, or error-handling behavior.
- Personally identifiable information (shipping name/address, customer email,
  display name, order notes) is stored encrypted at rest. Never persist PII in
  plaintext columns and never log decrypted PII.
- Do not create real invoices, trigger payments, or use production payment
  credentials unless the task explicitly requests it.

## Validation

- Add or update tests for every behavior change (`tests/`, pytest).
- Run the relevant tests, and run the full suite when practical:

  ```bash
  python -m pytest tests/ -q
  ```

- There is no frontend build step. Validate template, JavaScript, and
  translation changes with the applicable tests and lightweight syntax checks.
- Database schema changes go through the idempotent migration mechanism in
  `init_db.py` (`_ensure_column` and dedicated migration helpers), never
  destructive rewrites.

## Cost-effective delegation

- Use lower-cost subagents for bounded, mechanical, and easily verifiable
  work: repository exploration, call-site searches, focused test drafts,
  translation consistency checks, and narrow changes with explicit acceptance
  criteria.
- The primary agent owns user intent, architecture, security, and the final
  result. It must review every delegated change, inspect the final diff, run
  relevant validation, and report the outcome.
- Default to read-only delegation. Delegate implementation only when the scope,
  target files, acceptance criteria, and validation command are explicit; do
  not assign overlapping file edits to multiple agents (use separate git
  worktrees / branches per delegated task).
- Do not delegate final decisions or external actions. The primary agent must
  handle authentication, permissions, CSRF, payments, wallets, backups,
  secrets, database migrations, destructive operations, commits, pushes, pull
  requests, deployments, and credential changes.

## Git workflow

- Before starting a new feature or an independently scoped change, consider
  whether a dedicated branch would improve isolation. If it would, suggest a
  specific `feature/<topic>` branch name and ask for approval before creating
  or switching to it.
- Do not create or switch branches automatically. Continue on the current
  branch only when it is not `main` and the work fits that branch's scope. Do
  not implement new work directly on `main`; request approval for a feature
  branch instead.
- Create approved feature branches from an up-to-date `main` branch.
- Never commit or push directly to `main`. Integrate work through a reviewed
  pull request.
- Local commits on a feature branch are allowed after relevant validation
  passes. Do not push or create/update a pull request unless explicitly asked.
- Keep changes focused; do not overwrite or discard unrelated work in a dirty
  worktree.

## Secrets, local state, and operations

- Never commit secrets, `.env` files, API keys, production credentials, the
  `MASTER_MNEMONIC` / PII encryption seed, SQLite databases, encrypted
  backups, or local Claude settings.
- Keep `data/`, backup files, `.env` variants, private keys, and local
  `.claude/` state untracked. Only the shared `.claude/settings.json` may be
  versioned.
- Local server, Docker, database, and deployment commands are permitted when
  they are needed for the task (`docker-compose up`, gunicorn, pytest). Do not
  run destructive resets, delete or replace production data, alter production
  credentials, or restore a backup unless the task explicitly requests that
  action.
