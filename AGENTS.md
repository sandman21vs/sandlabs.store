# sandlabs.store Contributor and AI Operating Rules

This file is the canonical operating policy for everyone contributing to this
repository, including AI agents. `CLAUDE.md` only adds Claude-specific
shortcuts and defers to this document for all shared rules.

`sandlabs.store` is a Flask 3 + SQLite e-commerce app that sells hardware and
settles payments in Bitcoin (Lightning / Liquid / on-chain) through Coinos.
Data lives in SQLite (`data/sandlabs.db`); there is no ORM and no frontend
build step.

## How work lands: everything through pull requests

`main` only changes through pull requests that the maintainer reviews and
merges. This applies to humans and agents alike.

1. **Plan.** Non-trivial work starts from a plan the maintainer approved. The
   active plan and its checklist live in `docs/ROADMAP.md`.
2. **Branch.** One branch per phase, created from an up-to-date `main` or from
   the previous phase's branch when the work is stacked. Prefixes: `feature/`,
   `fix/`, `ui/`, `chore/`, `docs/`.
3. **Commit.** Small, focused commits in
   [Conventional Commits](https://www.conventionalcommits.org/) style
   (`feat(checkout): ...`, `fix(i18n): ...`), after the relevant tests pass.
4. **Push and open a PR.** One PR per phase, using
   `.github/pull_request_template.md`. Open it as a draft when it is not ready
   for review.
5. **Review and merge.** The maintainer reviews and merges. Address review
   feedback with new commits on the same branch.

### What agents may do without asking

When executing an approved plan, an agent may create the phase branch, commit
to it, push it, and open or update its pull request.

### What agents must never do

- Commit or push to `main`, or merge any pull request.
- Force-push, rewrite published history, or delete remote branches.
- Change repository settings, branch protection, secrets, or CI permissions.
- Start work that is outside the approved plan without asking first.
- Add AI attribution: no `Co-Authored-By` trailers for AI tools and no
  "generated with" lines in commits or pull requests.

### Stacked pull requests

- Each PR targets the branch of the phase it builds on and says so in its
  description (`Base: <branch>`, `Stack: 3/9`).
- Keep one concern per PR. A reviewer should be able to read it in one sitting.
- If a phase cannot reach green tests, stop the stack there: open that PR as a
  draft with the diagnosis and do not build dependent phases on top of it.
- Do not overwrite or discard unrelated work in a dirty worktree.

### Pull request description

Every PR states:

- **What and why** — the change and the problem it solves.
- **How it was tested** — the exact command and its result (for example
  `python -m pytest tests/ -q` → `273 passed`).
- **Visual evidence** — for UI changes, which pages were checked, at which
  viewport widths and in which languages.
- **Risk and rollback** — what could break, and whether reverting the PR is
  enough.

### Definition of done

- Tests added or updated for every behavior change; the full suite passes.
- User-facing copy exists in all four languages.
- `README.md` and `ARCHITECTURE.md` updated when setup, deployment, security,
  integrations, routes, or persisted-data behavior changed.
- `docs/ROADMAP.md` ticked for the finished phase.
- CI is green on the PR.

## Language and documentation

- Communicate with each user in their preferred language, and follow an
  explicitly stated change of preference.
- Write repository code, comments, commit messages, pull requests, and
  technical documentation in English.
- Keep the product intentionally multilingual. The store ships **four**
  languages: `pt` (default), `en`, `es`, and `de` (see `SUPPORTED_LANGS` in
  `i18n.py`). `translations/<lang>/*.json` and any user-facing PT/EN/ES/DE copy
  are exceptions to the English technical-language rule.
- Do not hardcode user-facing strings in templates or JavaScript; add a key to
  every `translations/<lang>/` file instead.
- Finished plans and briefs move to `docs/archive/`. They are history, not
  instructions.

## Architecture and product safeguards

- Follow the existing layering: route handlers (`routes/routes_*.py`) delegate
  to services (`services/service_*.py`), and services use the model/data layer
  (`models/model_*.py`). Keep route handlers thin. Services must not import
  Flask (the one allowed exception is `service_qr.py`, which uses `send_file`).
- Preserve CSRF protection (global in `app.py`; only the Coinos webhook is
  exempt), `login_required` / `admin_required` boundaries, i18n detection and
  fallbacks (`i18n.py`), HTML sanitization, and financial/accounting behavior
  (all money is handled in satoshis end-to-end).
- Prices are server-authoritative. The browser may display and choose, but the
  server recomputes every amount it charges.
- Treat Coinos credentials, carrier API credentials, wallet addresses, payment
  webhooks, invoice hashes, balances, the PII encryption key/seed, and
  encrypted customer data as security-sensitive. Coinos logic lives in
  `services/service_coinos.py`; at-rest encryption lives in
  `services/service_security.py`. Do not weaken their validation,
  authorization, audit, or error-handling behavior.
- Personally identifiable information (shipping name/address, customer email,
  display name, order notes, shipping labels) is stored encrypted at rest.
  Never persist PII in plaintext columns and never log decrypted PII.
- Send third parties only the PII a feature strictly needs.
- Do not create real invoices, trigger payments, buy shipping labels, or use
  production credentials unless the task explicitly requests it. External
  services are mocked in tests.

## Frontend

- No build step and no external CDNs: styles, scripts, and fonts are served
  from `static/`.
- Reuse the design tokens and components in `static/css/style.css` (and
  `static/css/admin.css` for the admin). Do not add inline `style=""`
  attributes or per-template `<style>` blocks.
- Every page must work from 375 px wide upward, be keyboard-navigable, and
  keep visible focus states.

## Validation

- Add or update tests for every behavior change (`tests/`, pytest).
- Run the relevant tests while iterating and the full suite before pushing:

  ```bash
  python -m pytest tests/ -q
  ```

- There is no frontend build step. Validate template, JavaScript, and
  translation changes with the applicable tests, and check UI changes in a
  browser against a local instance with a throwaway database.
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
