# Brief — Fase D: Frete híbrido DHL + Swiss Post (Codex, worktree)

## Contexto
Repo: sandlabs.store (Flask 3 + SQLite). Leia `AGENTS.md` e `CLAUDE.md` antes.
Hoje o frete usa uma tabela estática de tarifas Swiss Post em
`services/service_shipping.py` (`calculate_shipping_chf`, `get_country_zone`,
`get_shipping_rates`), editável no admin via config `shipping_rates`.

## Objetivo
Transformar o frete em **híbrido**: cotação por API real da transportadora
quando houver credenciais, com **fallback automático** para a tabela atual.

## Escopo / arquivos
- `services/service_shipping.py` — vira ORQUESTRADOR. Manter
  `calculate_shipping_chf` como fallback. Adicionar `get_shipping_options(weight_grams, country_code) -> list[dict]`
  retornando opções `{carrier, service, price_chf, price_sats, source}` onde
  `source ∈ {"dhl","post","table"}`.
- NOVOS: `services/service_shipping_dhl.py`, `services/service_shipping_post.py`.
  Cada um expõe `quote(weight_grams, country_code) -> list[dict] | None`.
  Chamam a API real só se as credenciais existirem (config: `dhl_api_key`,
  `post_api_key`, flags `dhl_enabled`/`post_enabled`). Em erro/ausência/timeout
  → retornar `None` (o orquestrador cai na tabela). Use `urllib.request` +
  `timeout=10`, logging com `logger.exception`, e NUNCA lance exceção pra cima.
- `routes/routes_checkout.py` — endpoint `/api/shipping/calculate` passa a
  devolver **lista de opções** (não um único valor). Não altere lógica de
  pagamento nem criação de pedido.
- `templates/checkout.html` + `static/js/checkout.js` — renderizar a escolha de
  opção de frete (radio), atualizar total ao selecionar.
- `models/model_config.py` / `templates/admin/settings.html` — campos para as
  credenciais/flags DHL/Post (apenas leitura/escrita no config key/value; sem
  migração de schema).

## Reuso
- `get_country_zone`, `get_shipping_rates` (fallback), `fiat_to_sats` de
  `services/service_btc_price.py`, padrão de client HTTP de
  `services/service_coinos.py`.

## Restrições (AGENTS.md)
- NÃO tocar em pagamentos, segredos, criptografia, migrações de schema
  (`init_db.py`), `main`, commits/push/PR. Só o agente primário faz isso.
- Sem edições sobrepostas com outras fases.

## Aceite
- `python -m pytest tests/ -q` verde (inclui novos testes).
- Novos testes: `tests/test_service_shipping.py` cobrindo (a) fallback quando
  sem credenciais, (b) parsing de resposta simulada da API (mock urllib),
  (c) `get_shipping_options` retornando múltiplas opções.
- Documentar no `README.md`/`ARCHITECTURE.md` que APIs reais exigem contas
  comerciais e como configurar as credenciais.
