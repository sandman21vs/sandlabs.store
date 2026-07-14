# Execution & Handoff — Integrations Roadmap

**Purpose.** This is the single source of truth for continuing the integrations
work on `sandlabs.store`. It is written so that an executor agent (Codex,
running as the orchestrating "brain") can read it and drive the remaining
phases to completion. Read `AGENTS.md` and `CLAUDE.md` first — they are the
operating policy this plan obeys.

**Communicate with the user in Portuguese.** Repo code/comments/commits in
English.

---

## Tick-off protocol (how to report progress)

When a phase is finished (its tests pass and it is committed), do all three:

1. Change its checkbox below from `[ ]` to `[x]` and append the commit hash.
2. Use a commit message `feat(<area>): ... (Fase X)`.
3. Keep the phase's brief in `docs/briefs/` up to date if the approach changed.

This checklist **is** the "tik de ok" the user asked for.

### Phase checklist

- [x] **Fase 0** — Governança (`AGENTS.md`, `CLAUDE.md`, briefs) — `0d1a890`
- [x] **Fase A** — Criptografia de PII com seed BIP39 — `13092ae`
- [x] **Fase B** — Padronização de schema (`orders`) — `45cfb2e`
- [x] **Fase C** — Pagamento onchain + Liquid (Coinos) — `ca788ae`
- [x] **Fase D** — Frete híbrido DHL + Swiss Post — `c1ea53e`
- [x] **Fase E** — Imagens: thumbnail + lupa/zoom — `c9507a6`
- [ ] **Fase F-pdf** — Geração do PDF do pedido — _brief: `docs/briefs/brief-F-pdf.md`_
- [ ] **Fase F-core** — Checkout como convidado + `access_token` — _owner: brain (auth/migration)_
- [ ] **Fase G** — Multi-moeda: USD + switcher — _brief: `docs/briefs/brief-G-moeda.md`_
- [ ] **Etapa 3** — Reconciliação, merge, atualizar `ARCHITECTURE.md`

---

## Current state

- **Branch:** `feature/integrations-foundation` (from `main` @ `6cc7fec`). All new
  work branches/worktrees from **this** branch (it already contains A+B), not
  from `main`.
- **Tests:** `237 passing`. Baseline was 207; A +9, B +2, C +7, D +8, E +4.
- **Fases 0/A/B/C/D/E are already committed on this branch** (not in separate
  worktrees). The remaining implementation covers F and G. C is done — the
  "reconciliation order" that lists C refers only to the case where it had been
  a separate worktree; here it needs no merge.
- **Do not push or open a PR** unless the user explicitly asks (AGENTS.md).

### What A+B delivered (foundation the other phases build on)
- PII encryption key + blind-index HMAC key derived from `MASTER_MNEMONIC`
  (BIP39 phrase; dev fallback `SHIPPING_DATA_KEY`/`SECRET_KEY`) via HKDF, in
  `services/service_security.py`. `MultiFernet` still decrypts legacy data.
  Helpers: `encrypt_value`, `decrypt_value`, `blind_index`, `email_blind_index`,
  `require_pii_key`.
- `users`: `email_enc` / `email_bidx` (UNIQUE) / `display_name_enc` — no
  plaintext email. Lookups via blind index in `models/model_users.py`.
- `orders`: legacy plaintext shipping columns dropped; **new columns already
  exist** for the phases below: `payment_method`, `invoice_type`, `btc_address`,
  `shipping_carrier`, `shipping_service`, `access_token`. See
  `models/model_orders.py` `_ORDER_SELECT` (they are already selected/normalized).

---

## How to run tests (important local caveat)

Production runs in Docker (`python:3.12-slim`, pinned `requirements.txt`).
Locally the system Python is 3.14, where pinned `Pillow==11.1.0` has no wheel,
so a gitignored `.venv` was created for validation with an unpinned Pillow:

```bash
python3 -m venv .venv
.venv/bin/pip install flask gunicorn qrcode Werkzeug cryptography pytest pillow
.venv/bin/python -m pytest tests/ -q
```

Git identity is set locally (`user.name "Sandmann"`,
`user.email viniciussoriano21vs@gmail.com`). Commit trailer:
`Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>` (adjust author as
appropriate for Codex).

---

## Orchestration model

The user runs Codex as the single orchestrating brain. Codex may execute the
remaining phases **serially itself**, or spawn its own subagents per phase.
Either way, respect these rules (AGENTS.md):

- **Brain-only (do not delegate):** Fase C (payments/wallets) and Fase F-core
  (auth/session + DB migration). Review every diff for these carefully.
- **Delegable / mechanical:** D, E, F-pdf, G — each is self-contained; if using
  worktrees, one branch per phase, **no overlapping file edits** between them.
- **Reconciliation order** (fewest conflicts first): E → G → D → F-pdf → C →
  F-core. Run `pytest` between each merge. Conflict hot-spots:
  `routes/routes_checkout.py`, `models/model_orders.py`, `init_db.py`.
- **One commit per phase after tests pass.** Update this checklist each time.

---

## Fase C — Pagamento onchain + Liquid (brain-owned, money)

**MVP is Lightning (already working).** Add Liquid + on-chain as additive,
behind an admin toggle. A **proven reference implementation exists** in the
user's other project: `~/prometeu/coinos_client.py` — port its patterns.

1. `services/service_coinos.py`: add `get_fresh_onchain_address()`,
   `get_fresh_liquid_address()` (both POST a 0-amount invoice of type
   `bitcoin`/`liquid` and return `hash` = address) and `get_received_sats()`.
   Copy the exact shape from `~/prometeu/coinos_client.py`. Gate on-chain behind
   a `coinos_onchain` config flag (mirror prometeu).
2. `routes/routes_checkout.py` `create_order` (invoice is currently hardcoded to
   Lightning around the `create_invoice(...)` call): let the buyer pick a method
   (Lightning / Liquid / On-chain). For Liquid/on-chain, generate a per-order
   address and store it in `orders.btc_address` + `orders.invoice_type` +
   `orders.payment_method` (columns already exist).
3. Confirmation: Lightning via existing webhook; Liquid/on-chain via polling
   `check_invoice(hash)` and marking paid when `received >= amount_sats` (reuse
   `/api/checkout/check-payment/<id>`). Coinos handles confirmations.
4. UI: `templates/payment.html` + `static/js/payment.js` (show address/QR per
   method, reuse `services/service_qr.py`); `templates/checkout.html` selector.
5. Admin toggles in `templates/admin/settings.html` + `routes/routes_admin.py`.
6. Tests: address generation (mock urllib), method selection, polling-confirms.
   Reference test: `~/prometeu/tests/test_coinos_addresses.py`.

**Acceptance:** `pytest` green; Lightning path unchanged; Liquid/on-chain
produce a stored per-order address and confirm via polling.

## Fase D — Frete híbrido DHL + Swiss Post

See `docs/briefs/brief-D-frete.md`. Orchestrator in `services/service_shipping.py`
with the current static table as fallback; real carrier APIs only when
credentials are configured; return multiple options to the checkout.

## Fase E — Imagens: thumbnail leve → alta resolução com lupa

See `docs/briefs/brief-E-imagens.md`. Cards use webp thumbnails (lazy); extend
the existing `static/js/lightbox.js` to load the high-res original with a zoom
lens.

## Fase F — PDF do pedido + checkout convidado

- **F-pdf** (delegable): see `docs/briefs/brief-F-pdf.md`. Add `fpdf2`, new
  `services/service_pdf.py` `build_order_pdf(order) -> bytes`, embed a tracking
  QR via `service_qr.py`. Pure function + test only.
- **F-core** (brain-owned): relax `login_required` on checkout to allow guest
  orders keyed by `session_id` + `orders.access_token` (column exists); add the
  PDF download route and a public order-lookup page (order id + token). This
  touches auth/session — keep CSRF and ownership checks intact.

## Fase G — Multi-moeda: USD + switcher

See `docs/briefs/brief-G-moeda.md`. Enable USD in `ADMIN_ENABLED_CURRENCIES`
(`services/service_pricing.py`) and add a display-currency switcher
(CHF/EUR/BRL/USD); settlement stays in sats.

## Etapa 3 — Reconciliação

Merge in the order above, `pytest` between merges, one commit per phase, then
update `ARCHITECTURE.md` (there is already a "Criptografia de PII" section from
Fase A to extend) and mark every checkbox `[x]` with its commit hash.
