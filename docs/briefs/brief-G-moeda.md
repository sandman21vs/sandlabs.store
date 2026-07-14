# Brief — Fase G: Multi-moeda (USD + switcher do cliente) (Sonnet, worktree)

## Contexto
Repo: sandlabs.store (Flask 3 + SQLite). Leia `AGENTS.md` e `CLAUDE.md` antes.
`services/service_pricing.py` já define `SUPPORTED_FIAT_CURRENCIES` = CHF, USD,
EUR, BRL, com conversão fiat→sats via `services/service_btc_price.py`
(CoinGecko, cache 5 min). Hoje `ADMIN_ENABLED_CURRENCIES = (SATS, "CHF")` — o
admin só deixa inserir preço em SATS ou CHF. Toda liquidação é em satoshis.

## Objetivo
1. Permitir inserir preço de produto também em **USD** no admin (além de CHF/SATS).
2. **Switcher de moeda de exibição** para o cliente (CHF/EUR/BRL/USD) com
   conversão ao vivo; a liquidação continua **sempre em sats**.

## Escopo / arquivos
- `services/service_pricing.py` — incluir `USD` em `ADMIN_ENABLED_CURRENCIES`.
- `templates/admin/product_form.html` — expor USD como opção de moeda de preço.
- `static/js/config-store.js` + render (`render-home.js`/`render-produtos.js`) —
  seletor de moeda de exibição; converter o preço exibido usando as taxas já
  disponíveis (reusar o que o backend expõe; se necessário, um endpoint leve
  de taxas — confirmar com o agente primário antes de criar rota nova).
- `templates/base.html` — ponto de UI para o switcher (perto do seletor de idioma).

## Reuso
- `SUPPORTED_FIAT_CURRENCIES`, `format_fiat_display`, `fiat_to_sats`,
  `service_btc_price.py`.

## Restrições (AGENTS.md)
- NÃO tocar em pagamentos, checkout, segredos, migrações, `main`, commits/PR.
- A liquidação é sempre em sats — o switcher é só exibição.
- Sem edições sobrepostas com outras fases.

## Aceite
- `python -m pytest tests/ -q` verde, com teste para USD habilitado em
  `ADMIN_ENABLED_CURRENCIES` e para pré-visualização/normalização de preço em USD.
- Verificação manual: admin cria produto com preço em USD; cliente troca moeda
  de exibição e vê valores convertidos; total do carrinho/checkout permanece em sats.
