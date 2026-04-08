# Checklist de Execução de i18n

## Fase 1 — Infraestrutura base

- [x] Criar `i18n.py`
- [x] Definir idiomas suportados: `pt`, `en`, `es`, `de`
- [x] Criar estrutura `translations/<lang>/`
- [x] Separar traduções por domínio:
  - [x] `common.json`
  - [x] `public.json`
  - [x] `commerce.json`
  - [x] `auth.json`
  - [x] `account.json`
  - [x] `admin.json`
  - [x] `catalog.json`
  - [x] `js.json`
- [x] Implementar fallback para `pt`
- [x] Resolver idioma por `session` / `Accept-Language`
- [x] Criar rota `/set-lang/<lang>`
- [x] Injetar `t()` nos templates
- [x] Injetar dicionário JS no layout base
- [x] Adaptar testes para inicializar i18n

## Fase 2 — Layout global

- [x] Traduzir `templates/base.html`
- [x] Traduzir navegação principal
- [x] Traduzir footer
- [x] Traduzir meta description
- [x] Traduzir OG description
- [x] Adicionar seletor de idioma visível
- [ ] Validar layout em mobile e desktop com seletor

## Fase 3 — Páginas públicas

- [x] Traduzir `templates/index.html`
- [x] Traduzir `templates/produtos.html`
- [x] Traduzir `templates/sobre.html`
- [x] Traduzir `templates/termos.html`
- [x] Traduzir `templates/suporte.html`
- [x] Traduzir `templates/404.html`
- [x] Traduzir `templates/500.html`
- [x] Preencher `translations/*/public.json`

## Fase 4 — Catálogo

- [x] Preparar localização do catálogo no backend
- [x] Mapear todos os produtos por `product.id`
- [x] Traduzir nome dos produtos
- [x] Traduzir resumo dos produtos
- [x] Traduzir `detalhesHTML`
- [x] Traduzir botão de compra
- [x] Traduzir badges
- [x] Traduzir labels de preço
- [x] Traduzir títulos de opções
- [x] Traduzir labels de inputs
- [x] Preencher `translations/*/catalog.json`

## Fase 5 — Frontend público

- [ ] Traduzir `static/js/render-home.js`
- [x] Traduzir `static/js/render-produtos.js`
- [x] Traduzir `static/js/lightbox.js`
- [x] Remover strings fixas de botões/modais
- [x] Remover strings fixas de `aria-label`
- [x] Remover strings fixas de `alert`/mensagens visuais
- [x] Preencher `translations/*/js.json` para área pública

## Fase 6 — Carrinho, checkout e pagamento

- [x] Traduzir `templates/cart.html`
- [x] Traduzir `templates/checkout.html`
- [x] Traduzir `templates/payment.html`
- [x] Traduzir mensagens em `routes/routes_cart.py`
- [x] Traduzir mensagens em `routes/routes_checkout.py`
- [x] Traduzir `static/js/cart.js`
- [x] Traduzir `static/js/compras.js`
- [x] Preencher `translations/*/commerce.json`

## Fase 7 — Auth e conta

- [ ] Traduzir `templates/auth/login.html`
- [ ] Traduzir `templates/auth/register.html`
- [ ] Traduzir `templates/account/orders.html`
- [ ] Traduzir `templates/account/order_detail.html`
- [ ] Traduzir mensagens em `routes/routes_auth.py`
- [ ] Preencher `translations/*/auth.json`
- [ ] Preencher `translations/*/account.json`

## Fase 8 — Admin e config

- [ ] Traduzir `templates/admin/base_admin.html`
- [ ] Traduzir `templates/admin/dashboard.html`
- [ ] Traduzir `templates/admin/products.html`
- [ ] Traduzir `templates/admin/product_form.html`
- [ ] Traduzir `templates/admin/orders.html`
- [ ] Traduzir `templates/admin/order_detail.html`
- [ ] Traduzir `templates/admin/settings.html`
- [ ] Traduzir `templates/admin/setup.html`
- [ ] Traduzir `templates/config.html`
- [ ] Traduzir mensagens em `routes/routes_admin.py`
- [ ] Traduzir `static/js/config-page.js`
- [ ] Preencher `translations/*/admin.json`

## Fase 9 — Traduções finais

- [ ] Consolidar `pt` como base canônica
- [ ] Completar `en`
- [ ] Completar `es`
- [ ] Completar `de`
- [ ] Revisar consistência terminológica
- [ ] Revisar tom comercial e técnico

## Fase 10 — Testes e validação

- [x] Criar `tests/test_i18n.py`
- [ ] Validar `/set-lang/<lang>`
- [ ] Validar `Accept-Language`
- [ ] Validar fallback para `pt`
- [ ] Validar cobertura de chaves entre idiomas
- [ ] Validar render das páginas principais por idioma
- [ ] Validar carrinho/checkout por idioma
- [ ] Validar admin por idioma

## Execução paralela

- [x] Separar trabalho por domínio para agentes mais baratos
- [ ] Integrar lote de páginas públicas
- [ ] Integrar lote de commerce/auth/account
- [ ] Integrar lote de admin/config
- [ ] Rodar revisão final de consistência

## Fechamento

- [ ] Atualizar documentação do projeto para refletir i18n
- [ ] Remover referências antigas que assumem site monolíngue
- [ ] Confirmar estratégia futura para novos idiomas
