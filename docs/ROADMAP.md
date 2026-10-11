# Roadmap

The active plan for `sandlabs.store`. Each phase is one branch and one pull
request, stacked on the previous one. Tick a phase when its tests pass and its
PR is open; add the PR link.

Rules for executing this plan are in `AGENTS.md`.

## Stack

- [x] **1. Agent governance** — `chore/agent-governance` — [#1](https://github.com/sandman21vs/sandlabs.store/pull/1)
  PR-based workflow in `AGENTS.md`, rewritten `README.md`, archived finished
  plans, PR template, CI.
- [x] **2. UI overhaul base** — `ui/01-overhaul-base` — [#2](https://github.com/sandman21vs/sandlabs.store/pull/2)
  Bring the unmerged `feature/ui-ux-overhaul` work (tokens, mobile navigation,
  card grid, product page) into the stack.
- [x] **3. Design system** — `ui/02-design-system` — [#3](https://github.com/sandman21vs/sandlabs.store/pull/3)
  Revised tokens, system font stack, one set of buttons, forms, cards, badges,
  tables and alerts; calmer background; focus and reduced-motion support.
- [x] **4. Storefront** — `ui/03-storefront` — [#4](https://github.com/sandman21vs/sandlabs.store/pull/4)
  Header, footer, home, catalog, product, about, support, terms, error pages.
- [ ] **5. Purchase flow** — `ui/04-purchase-flow`
  Cart, checkout, payment, order lookup, account and auth pages. Presentation
  only; no pricing or payment logic changes.
- [ ] **6. Admin** — `ui/05-admin`
  `static/css/admin.css` replaces inline styles; hardcoded strings move to the
  translation catalogs; responsive tables.
- [ ] **7. Swiss Post rates** — `feature/swisspost-01-rates`
  PostPac Economy and Priority as separate options for Switzerland; remove the
  placeholder rate endpoint.
- [ ] **8. Swiss Post address validation** — `feature/swisspost-02-address`
  Digital Commerce API client (OAuth2 client credentials) and non-blocking
  address validation for Swiss destinations at checkout.
- [ ] **9. Swiss Post labels** — `feature/swisspost-03-labels`
  Label generation from the admin order page, encrypted label storage,
  automatic tracking code, tracking link for customers.

## Notes

- The Swiss Post Digital Commerce API has no price endpoint. Prices come from
  the admin-editable rate table.
- Swiss Post integrations ship disabled and are tested with mocked HTTP. They
  need a Swiss Post business account, API credentials from
  <https://developer.post.ch> and, for labels, a franking licence.

## Maintainer follow-ups

- Enable branch protection on `main` (require a pull request and green CI).
- Request Swiss Post API credentials and validate address checks and SPECIMEN
  labels against the real service.
