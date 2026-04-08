# Plano de Implementação de Internacionalização

## Objetivo

Adicionar suporte multilíngue ao `sandlabs.store` com os idiomas:

- `pt` — português
- `en` — inglês
- `es` — espanhol
- `de` — alemão

O objetivo não é apenas "traduzir textos soltos", mas reorganizar o projeto para que:

- a troca de idioma seja nativa do app;
- novos idiomas possam ser adicionados sem retrabalho estrutural;
- textos de template, backend, frontend e catálogo tenham uma fonte de verdade clara;
- a manutenção futura não dependa de caçar strings espalhadas pelo código.

Este plano reaproveita o padrão observado em `/home/server/FREESANDMANN`, adaptado ao contexto atual de Flask + Jinja + JavaScript do `sandlabs.store`.

---

## Estado Atual

Hoje o projeto tem texto hardcoded em vários lugares:

- templates Jinja
- rotas Flask com mensagens de erro/sucesso
- JavaScript do frontend
- conteúdo do catálogo de produtos
- labels e mensagens do admin

Além disso:

- o catálogo é injetado como `window.PRODUTOS`;
- o frontend depende de várias strings embutidas em JS;
- não havia uma camada central de i18n;
- não havia testes específicos para idioma, fallback e consistência de chaves.

---

## Direção Arquitetural

### Camada central de i18n

Foi definida uma arquitetura com:

- `i18n.py` como módulo central
- `translations/<lang>/*.json` como fonte de traduções
- `t('chave')` disponível em templates
- resolução de idioma por:
  - `session`
  - `Accept-Language`
  - fallback para `pt`
- rota `/set-lang/<lang>` para troca manual de idioma

### Organização das traduções

As traduções foram divididas por domínio para evitar arquivos gigantes e permitir trabalho paralelo:

- `common.json`
- `public.json`
- `commerce.json`
- `auth.json`
- `account.json`
- `admin.json`
- `catalog.json`
- `js.json`

Isso permite que cada área do sistema evolua isoladamente e reduz conflitos entre mudanças paralelas.

### Catálogo

O catálogo precisa ser tratado como uma área separada, porque não envolve só labels visuais:

- nome do produto
- resumo
- detalhes HTML
- botão de compra
- badge
- labels de preços
- títulos de opções e labels de inputs

Por isso, o plano prevê localização do catálogo em `translations/<lang>/catalog.json`, com mapeamento por `product.id`.

---

## Fases

## Fase 1 — Infraestrutura base de i18n

### Objetivo

Criar a espinha dorsal da internacionalização antes de traduzir qualquer área grande.

### Escopo

- criar `i18n.py`
- carregar traduções por idioma
- expor helper `t()` no Jinja
- resolver idioma atual por sessão/header
- adicionar rota de troca manual de idioma
- injetar traduções JS no layout base
- adaptar `app.py` e ambiente de testes

### Entregáveis

- módulo central de i18n
- pastas `translations/pt`, `translations/en`, `translations/es`, `translations/de`
- arquivos JSON por domínio
- suporte a `lang` e `supported_langs` em templates
- testes básicos de idioma e fallback

### Critério de aceite

- o app renderiza com idioma selecionado sem quebrar rotas existentes;
- `t('...')` funciona no layout base;
- `/set-lang/en` e equivalentes atualizam a sessão;
- fallback para `pt` funciona.

### Riscos

- templates antigos podem assumir strings fixas;
- testes que montam o app manualmente podem ignorar a nova infraestrutura se não forem atualizados.

---

## Fase 2 — Layout global e navegação

### Objetivo

Traduzir a moldura compartilhada do site para que o idioma já seja visível em todas as páginas.

### Escopo

- `templates/base.html`
- navegação principal
- footer
- meta tags
- labels de idioma
- páginas de erro globais

### Entregáveis

- header multilíngue
- footer multilíngue
- seletor de idioma visível
- meta description e og description traduzíveis
- `404` e `500` internacionalizados

### Critério de aceite

- o idioma muda o texto da navegação em qualquer página;
- o seletor de idioma funciona;
- páginas de erro respeitam o idioma atual.

### Riscos

- mudanças no layout base afetam todo o projeto;
- qualquer string esquecida nessa fase vaza português para todos os idiomas.

---

## Fase 3 — Páginas públicas

### Objetivo

Traduzir a área de marketing/conteúdo aberta ao visitante.

### Escopo

- `templates/index.html`
- `templates/produtos.html`
- `templates/sobre.html`
- `templates/termos.html`
- `templates/suporte.html`

### Entregáveis

- home em 4 idiomas
- páginas institucionais em 4 idiomas
- chamadas de ação e blocos textuais traduzidos

### Critério de aceite

- cada página pública renderiza sem texto hardcoded em português;
- os títulos e CTAs mudam de acordo com o idioma.

### Riscos

- páginas institucionais têm bastante texto autoral;
- traduções literais podem perder tom, então precisam ser revisadas com cuidado.

---

## Fase 4 — Catálogo de produtos

### Objetivo

Separar conteúdo estrutural do conteúdo textual dos produtos.

### Escopo

- localizar `window.PRODUTOS` a partir do backend
- mapear `product.id` -> tradução
- traduzir:
  - nome
  - resumo
  - detalhes HTML
  - botão de compra
  - badge
  - labels de preços
  - títulos de opções
  - labels dos inputs

### Entregáveis

- catálogo traduzível por idioma
- `catalog.json` por idioma
- função de localização do catálogo antes da injeção no frontend

### Critério de aceite

- os mesmos produtos aparecem em todos os idiomas;
- apenas o conteúdo textual muda;
- o frontend continua recebendo um `window.PRODUTOS` compatível com o código existente.

### Riscos

- parte do histórico do projeto ainda referencia `static/js/produtos-data.js`;
- existe risco de documentação antiga divergir da fonte real do catálogo;
- `detalhesHTML` exige cuidado para traduzir sem quebrar links/markup.

---

## Fase 5 — Frontend JS do catálogo e navegação comercial

### Objetivo

Remover strings fixas do JavaScript do visitante.

### Escopo

- `static/js/render-home.js`
- `static/js/render-produtos.js`
- `static/js/lightbox.js`
- demais scripts que exibem labels e mensagens ao usuário

### Entregáveis

- uso de `window.t('...')` no JS
- chaves em `translations/<lang>/js.json`
- labels de modal, lightbox, botões e mensagens dinâmicas traduzíveis

### Critério de aceite

- modais, botões e mensagens geradas por JS mudam com o idioma;
- não restam textos visíveis hardcoded em JS nessas áreas.

### Riscos

- JS antigo tem bastante string embutida e pouca separação semântica;
- é fácil esquecer textos em atributos `aria-label`, `alert`, `confirm` e `innerHTML`.

---

## Fase 6 — Carrinho, checkout e pagamento

### Objetivo

Traduzir a jornada comercial principal.

### Escopo

- `templates/cart.html`
- `templates/checkout.html`
- `templates/payment.html`
- `routes/routes_cart.py`
- `routes/routes_checkout.py`
- `static/js/cart.js`
- `static/js/checkout.js`
- `static/js/compras.js`

### Entregáveis

- labels do carrinho traduzidas
- mensagens de erro e validação traduzidas
- resumo do pedido traduzido
- mensagens geradas no frontend traduzíveis

### Critério de aceite

- usuário consegue comprar em qualquer idioma suportado;
- erros de validação aparecem no idioma correto;
- scripts de carrinho e checkout não exibem português fixo.

### Riscos

- backend e frontend compartilham conceitos, mas não a mesma fonte de texto;
- mensagens de erro de rota precisam passar a usar `i18n.translate(...)`;
- o fluxo comercial é sensível, então qualquer regressão aqui é crítica.

---

## Fase 7 — Autenticação e conta do usuário

### Objetivo

Traduzir login, registro e acompanhamento de pedidos.

### Escopo

- `templates/auth/login.html`
- `templates/auth/register.html`
- `templates/account/orders.html`
- `templates/account/order_detail.html`
- `routes/routes_auth.py`

### Entregáveis

- formulários de auth em 4 idiomas
- mensagens de erro/sucesso traduzidas
- páginas de pedidos traduzidas

### Critério de aceite

- login e cadastro funcionam com mensagens localizadas;
- conta do usuário não mistura idiomas.

### Riscos

- algumas mensagens de erro hoje estão direto nas rotas;
- fluxos com `next_url` e rate limit precisam continuar intactos.

---

## Fase 8 — Admin e painel de configuração

### Objetivo

Traduzir a área administrativa sem quebrar a operação do site.

### Escopo

- templates admin
- `routes/routes_admin.py`
- `templates/config.html`
- `static/js/config-page.js`

### Entregáveis

- dashboard admin traduzido
- gestão de produtos/pedidos/configurações traduzida
- setup inicial traduzido
- painel de configuração compatível com múltiplos idiomas

### Critério de aceite

- admin pode operar o sistema inteiro em qualquer idioma suportado;
- mensagens de flash, erro e confirmação estão internacionalizadas.

### Riscos

- o admin tem muito texto, labels e estados;
- parte do texto é técnico e precisa consistência terminológica;
- qualquer erro aqui afeta manutenção futura do catálogo e da loja.

---

## Fase 9 — Tradução efetiva dos 4 idiomas

### Objetivo

Popular os arquivos de tradução depois que as chaves estiverem estáveis.

### Estratégia

- `pt` vira a base canônica
- `en`, `es`, `de` são gerados a partir dela
- revisão manual posterior só nas áreas mais sensíveis

### Entregáveis

- cobertura total das chaves nos 4 idiomas

### Critério de aceite

- todas as chaves existentes em `pt` existem em `en`, `es`, `de`
- fallback só é usado excepcionalmente

### Riscos

- traduzir cedo demais gera retrabalho;
- traduzir strings antes de estabilizar chaves consome tokens à toa.

---

## Fase 10 — Testes e validação

### Objetivo

Garantir que i18n não quebre o comportamento funcional do site.

### Escopo

- testes de idioma por `Accept-Language`
- testes da rota `/set-lang/<lang>`
- testes de fallback
- testes de presença de chaves
- testes de render das páginas principais

### Entregáveis

- `tests/test_i18n.py`
- validação de cobertura de chaves

### Critério de aceite

- nenhum idioma suportado quebra renderização;
- chaves faltantes são detectadas por teste;
- fallback para `pt` continua previsível.

### Riscos

- este ambiente local não tem todas as dependências instaladas para rodar a suíte completa fora do container;
- validação completa depende de ambiente de runtime mais próximo do deploy.

---

## Estratégia de Execução com Agentes Mais Baratos

Como você pediu economia de tokens, a divisão correta do trabalho é:

1. estabilizar a infraestrutura central no agente principal;
2. dividir a migração por domínio;
3. mandar agentes baratos traduzirem apenas blocos delimitados.

### Divisão recomendada

- Agente A: páginas públicas + catálogo visual
- Agente B: carrinho + checkout + auth + conta
- Agente C: admin + config
- Agente D: geração/revisão dos JSONs `en/es/de`
- Agente E: testes de cobertura

### Por que isso economiza tokens

- cada agente recebe só os arquivos relevantes;
- evita reler o repositório inteiro a cada subtarefa;
- reduz colisão de edição;
- separa "infra" de "conteúdo traduzido".

---

## Ordem Recomendada de Entrega

1. Fase 1 — Infra de i18n
2. Fase 2 — Layout base
3. Fase 3 — Páginas públicas
4. Fase 4 — Catálogo
5. Fase 5 — JS público
6. Fase 6 — Carrinho e checkout
7. Fase 7 — Auth e conta
8. Fase 8 — Admin
9. Fase 9 — Traduções finais
10. Fase 10 — Testes e validação

---

## Resultado Esperado ao Final

Ao final dessa implementação, o projeto terá:

- arquitetura real de i18n
- idioma selecionável por sessão
- backend, templates e JS internacionalizáveis
- catálogo preparado para múltiplos idiomas
- base para adicionar novos idiomas no futuro com baixo custo
- menor acoplamento entre texto e lógica

Isso transforma a tradução de uma intervenção pontual em uma capacidade permanente do projeto.
