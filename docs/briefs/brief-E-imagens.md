# Brief — Fase E: Imagens (thumbnail leve → alta resolução com lupa) (Codex, worktree)

## Contexto
Repo: sandlabs.store (Flask 3 + SQLite). Leia `AGENTS.md` e `CLAUDE.md` antes.
Thumbnails webp já são gerados por `services/service_images.py` (max width 400,
q80) em `static/images/thumb/*.webp`. Já existe `static/js/lightbox.js` (modal
com prev/next, teclado, i18n via `window.t`).

## Objetivo
Grade/cards carregam **miniatura leve** (webp thumb, lazy). Ao clicar/abrir,
carrega o **original em alta resolução** com uma **lente de aumento (lupa)**.

## Escopo / arquivos
- `static/js/render-home.js`, `static/js/render-produtos.js` — usar o caminho do
  thumbnail webp para os cards (fallback pro original se thumb não existir) e
  `loading="lazy"` + `decoding="async"`.
- `static/js/lightbox.js` — ao abrir, trocar o `src` para o **original em alta**
  (não o thumb); adicionar **lente de aumento**: no desktop, zoom seguindo o
  mouse (lens/background-position) sobre a imagem; no mobile, pinch-to-zoom.
  Manter prev/next, ESC, acessibilidade e o helper `t()` existentes.
- `static/css/style.css` — SOMENTE ADICIONAR classes novas (`.lightbox-zoom`,
  `.zoom-lens`, etc.). Não modificar classes existentes.
- `services/service_images.py` / `scripts/generate_thumbnails.py` — garantir que
  o original em alta é preservado e que o helper para resolver o caminho do
  thumbnail existe/é exportado (ex.: `thumb_path(filename)`).

## Reuso
- `lightbox.js` existente (estender, não reescrever do zero).
- Pipeline de thumbnails em `service_images.py`.

## Restrições (AGENTS.md)
- NÃO tocar em pagamentos, checkout, segredos, migrações, `main`, commits/PR.
- `style.css`: apenas adicionar classes; não alterar as existentes.
- Sem edições sobrepostas com outras fases.

## Aceite
- `python -m pytest tests/ -q` verde.
- Novos testes onde aplicável (ex.: `tests/test_service_images.py` para o
  resolvedor de caminho de thumbnail). Front-end validado por checagem de
  sintaxe (`node --check static/js/lightbox.js`) já que não há build.
- Verificação manual descrita: card mostra thumb; clique abre alta resolução;
  lupa funciona no hover; funciona em mobile (pinch).
