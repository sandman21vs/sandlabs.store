# Arquitetura sandlabs.store — Guia para Agentes de Desenvolvimento

## Visao Geral

O sandlabs.store esta sendo convertido de um site estatico (HTML/CSS/JS puro servido por Nginx) para uma loja completa com backend Flask, banco SQLite, carrinho de compras, pagamento Bitcoin Lightning via Coinos API, calculo de frete via Post.ch, autenticacao de usuarios e painel admin.

**Stack:** Python 3.12 + Flask + SQLite + Jinja2 + Vanilla JS + CSS
**Pagamento:** Somente Bitcoin Lightning/on-chain via Coinos API
**Frete:** Post.ch (Correios Suicos) — domestico e internacional
**Deploy:** Docker + Gunicorn
**Referencia de codigo:** O projeto `/home/msi/FREESANDMANN/` contem a integracao Lightning ja funcionando em Flask e deve ser usado como base para adaptar pagamentos, QR codes, CSRF, e seguranca.

---

## Estado Atual (Fase 9 Completa + Ajustes Pos-Fase 9)

As Fases 1, 2, 3, 4, 5, 6, 7, 8 e 9 ja foram implementadas. O projeto ja possui:

- Flask servindo as paginas publicas com rotas limpas e redirects `.html` legados
- Produtos servidos do SQLite e injetados no frontend como `window.PRODUTOS`
- Carrinho com sessao anonima, endpoints JSON, badge no header e pagina `/carrinho`
- Autenticacao com registro/login/logout, CSRF global, headers de seguranca e area `/account/orders`
- Setup inicial em `/admin/setup`, inspirado no FREESANDMANN, com criacao do primeiro admin, definicao da senha e login imediato no painel
- Checkout autenticado com criacao de pedidos, invoice Lightning via Coinos, QR code, polling e webhook de confirmacao
- Calculo de frete Post.ch integrado ao checkout, com conversao CHF -> sats via `service_btc_price.py`
- Painel admin para produtos, pedidos e configuracoes, com tracking/status de pedidos alinhados ao schema atual
- Configuracoes do Coinos persistidas no SQLite via `/admin/setup` e `/admin/settings`, com prioridade sobre o `.env` durante o runtime de checkout e webhook
- Pricing dinamico por moeda: cada `product_price` pode ser salvo em `SATS` ou fiat; no momento da compra, valores em CHF sao convertidos para sats usando a cotacao BTC atual
- Galeria e cards usando thumbnails WebP em `static/images/thumb/`, com fallback para a imagem original e geracao automatica em uploads do admin
- Flash messages globais, metadados SEO/Open Graph, endpoint `/health`, logging adicional em checkout/admin, Docker multi-stage com usuario non-root e healthcheck
- Exibicao de sats ao lado dos precos fiat no payload `window.PRODUTOS`, e limpeza dos arquivos HTML/CSS/JS/imagens legados da raiz do repositorio

### Registro de execucao

- Fase 2 executada no commit `c9a024f` — banco SQLite, inicializacao, model de produtos e seed
- Fase 3 executada no commit `62d7383` — carrinho, APIs `/api/cart`, badge no header e pagina `/carrinho`
- Fase 4 executada no commit `e6a403d` — autenticacao, CSRF, bootstrap de admin e area de pedidos
- Fase 5 executada no commit `2019500` — checkout, criacao de orders, invoice Coinos, QR, polling e webhook
- Fase 6 executada no commit `ebcea21` e integrada ao checkout no commit `2019500` — calculo de frete Post.ch + conversao BTC/CHF
- Fase 7 executada no commit `394588e` e corrigida no commit `5e069ee` — painel admin e alinhamento do tracking/status ao schema de pedidos
- Fase 8 executada no commit `f4dff62` — service de thumbnails, script batch, frontend servindo thumbs e 44 thumbnails gerados
- Fase 9 executada no commit `790ae88` — polish final, SEO, `/health`, Docker de producao, precos em sats e limpeza dos legados da raiz
- Ajuste pos-Fase 9 executado no commit `32a38f2` — setup inicial estilo wizard, Coinos configuravel via UI e runtime alinhado ao banco
- Ajuste pos-Fase 9 executado no commit `46a116d` — pricing multi-moeda com conversao dinamica fiat -> sats no carrinho e checkout
- Suite de testes apos o ajuste de pricing: `pytest tests/ -q` -> `201 passed`

### Convencao de rastreabilidade

- Cada fase ou bloco relevante de alteracoes deve ser finalizado em commit separado, com mensagem descritiva.
- Apos concluir uma fase, atualizar este `ARCHITECTURE.md` para refletir o estado atual e registrar que a fase foi executada.

### Estado atual do pricing

- O schema `product_prices` aceita dois modos: `pricing_mode='sats'` ou `pricing_mode='fiat'`.
- Para precos em fiat, o banco guarda `currency_code` e `amount_fiat`; o valor em sats e resolvido no carrinho e no checkout usando a cotacao BTC atual.
- A UI do admin hoje esta priorizada para `SATS` e `CHF`, que cobrem o fluxo operacional atual da loja.
- O backend ja esta preparado para outras moedas fiat suportadas pelo service de cotacao, hoje: `USD`, `BRL` e `EUR`.
- Produtos legados com `display_text` antigo continuam sendo interpretados pelo backend para evitar quebra de compatibilidade.
- O pedido continua sendo fechado em sats no momento da compra, ou seja: o valor Lightning cobrado e sempre um snapshot da cotacao daquele instante.

### Roadmap sugerido para futuras adicoes

1. Expandir a UI do admin para permitir selecao explicita de `USD`, `BRL`, `EUR` e outras moedas suportadas, em vez de expor so `CHF` e `SATS`.
2. Persistir no `order_items` um snapshot completo do preco no momento da compra: `pricing_mode`, `currency_code`, `amount_fiat`, `btc_rate_used` e `unit_sats_resolved`, para auditoria e rastreabilidade historica.
3. Adicionar cache/telemetria de cotacao com fallback controlado no admin, para que a loja sinalize claramente quando a conversao fiat -> sats estiver indisponivel.
4. Permitir exibicao multi-moeda no frontend publico: por exemplo mostrar `CHF + sats` agora e futuramente alternar para `USD`, `EUR`, `BRL` por configuracao global ou preferencia do visitante.
5. Criar testes especificos para regressao de moedas futuras, cobrindo parser legados, arredondamento decimal, snapshot de pedido e indisponibilidade do feed de preco.

### Arquivos ja criados

```
app.py                     # Flask app, static_url_path="", redirects .html legados
config.py                  # SECRET_KEY, DATABASE_PATH, COINOS_* como defaults de bootstrap via env
db.py                      # get_db() com sqlite3.Row + WAL mode + foreign_keys
requirements.txt           # Flask==3.1.0, gunicorn==23.0.0, Pillow==11.1.0, qrcode==8.0
gunicorn.conf.py           # bind 0.0.0.0:8000, 2 workers, preload
Dockerfile                 # python:3.12-slim + gunicorn
docker-compose.yml         # port 8080:8000, volume ./data:/app/data
.env.example               # Template de variaveis de ambiente e bootstrap opcional do admin/Coinos

routes/
  __init__.py
  routes_public.py         # Blueprint "public" com rotas /, /produtos, /sobre, /termos, /suporte, /config

models/__init__.py         # Vazio (pacote)
models/model_config.py     # Config key-value com fallback para env, setup inicial e Coinos runtime
services/__init__.py       # Vazio (pacote)
services/service_pricing.py # Resolucao de preco em SATS/fiat e conversao dinamica para sats

templates/
  base.html                # Layout Jinja2 (header/nav/footer/bg-blobs, block content/scripts/footer)
  index.html               # Pagina inicial com hero + cards dinamicos
  produtos.html            # Pagina de produtos com galeria + lightbox
  sobre.html               # Pagina sobre
  termos.html              # Pagina termos
  suporte.html             # Pagina suporte
  config.html              # Pagina config (admin localStorage legado)
  404.html                 # Erro 404
  500.html                 # Erro 500

static/
  css/style.css            # CSS original (2450+ linhas, design tokens, glassmorphism, dark theme)
  js/                      # Todos os JS originais copiados sem alteracao
  images/                  # Todas as imagens PNG originais (~50 arquivos)
```

### Decisoes tecnicas da Fase 1

1. **`static_url_path=""`** — Flask serve arquivos estaticos na raiz em vez de `/static/`. Isso permite que todo o JS existente funcione sem alteracao (paths como `images/jade1.png` resolvem para `/images/jade1.png` servido de `static/images/`).

2. **Redirects `.html` legados** — O JS `render-home.js` usa `location.href='produtos.html'`. O `app.py` contem uma rota `/<page>.html` que redireciona 301 para a URL limpa (ex: `/produtos.html` -> `/produtos`), incluindo query strings (para cupom).

3. **Template heranca** — `base.html` extrai o layout comum. Cada pagina estende com `{% block content %}`, `{% block scripts %}`, `{% block footer %}`. A variavel `active` controla o nav-link ativo.

### Como rodar

```bash
# Desenvolvimento local
pip install -r requirements.txt
python app.py
# Acesse http://localhost:8000

# Docker
docker compose up --build
# Acesse http://localhost:8080
```

Se `ADMIN_PASSWORD` estiver vazio, o primeiro acesso ao painel admin deve passar por `/admin/setup`.

### Verificacao da Fase 1

Todas as rotas retornam 200, redirects .html funcionam com 301, arquivos estaticos (CSS, JS, imagens de produtos, cores) sao servidos corretamente, query strings sao propagadas nos redirects.

---

## Fase 2: Banco de Dados + Migracao de Produtos

**Objetivo:** Produtos servidos do SQLite. O JS existente continua funcionando sem alteracao.

### Arquivos a criar

#### `init_db.py`

Criar arquivo na raiz que cria todas as tabelas quando importado. Usar `db.get_db()` para conexao. Deve ser chamado em `app.py` antes de registrar blueprints.

```sql
-- Configuracao site (key-value)
CREATE TABLE IF NOT EXISTS config (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

-- Produtos
CREATE TABLE IF NOT EXISTS products (
    id            TEXT PRIMARY KEY,        -- slug: 'jade', 'pico', 'nerd'
    name          TEXT NOT NULL,
    summary       TEXT NOT NULL,
    details_html  TEXT NOT NULL DEFAULT '',
    weight_grams  INTEGER DEFAULT 200,
    buy_button_text TEXT NOT NULL DEFAULT 'Comprar',
    allow_addon_seed INTEGER DEFAULT 0,
    badge_text    TEXT,
    badge_variant TEXT,                    -- 'promo', 'new', 'neutral'
    sort_order    INTEGER DEFAULT 0,
    active        INTEGER DEFAULT 1,
    created_at    TEXT DEFAULT (datetime('now')),
    updated_at    TEXT DEFAULT (datetime('now'))
);

-- Precos (um produto pode ter varios)
CREATE TABLE IF NOT EXISTS product_prices (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id  TEXT NOT NULL,
    label       TEXT NOT NULL,             -- 'Jade DIY', 'Box de Protecao'
    amount_sats INTEGER NOT NULL,          -- usado diretamente quando pricing_mode='sats'
    pricing_mode TEXT,                     -- 'sats' ou 'fiat'
    currency_code TEXT,                    -- 'SATS', 'CHF', 'USD', 'BRL', 'EUR'...
    amount_fiat TEXT,                      -- valor fiat como decimal string
    display_text TEXT NOT NULL,            -- 'CHF 149.00' ou '5 000 sats'
    sort_order  INTEGER DEFAULT 0,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
);

-- Imagens do produto
CREATE TABLE IF NOT EXISTS product_images (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id  TEXT NOT NULL,
    filename    TEXT NOT NULL,             -- ex: 'images/jade1.png'
    sort_order  INTEGER DEFAULT 0,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
);

-- Opcoes de customizacao
CREATE TABLE IF NOT EXISTS product_options (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id  TEXT NOT NULL,
    option_type TEXT NOT NULL,             -- 'colorPair', 'colorSingle', 'seedPack'
    title       TEXT NOT NULL DEFAULT '',
    config_json TEXT NOT NULL DEFAULT '{}', -- JSON com inputs/input conforme tipo
    sort_order  INTEGER DEFAULT 0,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
);

-- Paleta de cores (compartilhada)
CREATE TABLE IF NOT EXISTS colors (
    id   TEXT PRIMARY KEY,                -- 'amarelo', 'azul', 'preto'
    name TEXT NOT NULL                    -- 'Amarelo', 'Azul', 'Preto'
);

-- Usuarios (para Fases 4+)
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    email         TEXT UNIQUE NOT NULL,
    display_name  TEXT NOT NULL DEFAULT '',
    password_hash TEXT NOT NULL,
    is_admin      INTEGER DEFAULT 0,
    created_at    TEXT DEFAULT (datetime('now'))
);

-- Carrinho (para Fase 3+)
CREATE TABLE IF NOT EXISTS cart_items (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id    TEXT,
    user_id       INTEGER,
    product_id    TEXT NOT NULL,
    price_id      INTEGER NOT NULL,
    quantity      INTEGER DEFAULT 1,
    options_json  TEXT DEFAULT '{}',
    created_at    TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (product_id) REFERENCES products(id),
    FOREIGN KEY (price_id) REFERENCES product_prices(id),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Pedidos (para Fase 5+)
CREATE TABLE IF NOT EXISTS orders (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id               INTEGER,
    session_id            TEXT,
    status                TEXT DEFAULT 'pending',   -- pending/paid/processing/shipped/delivered/cancelled
    total_sats            INTEGER NOT NULL,
    shipping_sats         INTEGER DEFAULT 0,
    invoice_hash          TEXT,
    bolt11                TEXT,
    payment_confirmed_at  TEXT,
    shipping_name         TEXT,
    shipping_address      TEXT,
    shipping_postal_code  TEXT,
    shipping_country      TEXT DEFAULT 'CH',
    shipping_tracking     TEXT,
    coupon_code           TEXT,
    notes                 TEXT DEFAULT '',
    created_at            TEXT DEFAULT (datetime('now')),
    updated_at            TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Itens do pedido
CREATE TABLE IF NOT EXISTS order_items (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id      INTEGER NOT NULL,
    product_id    TEXT NOT NULL,
    price_id      INTEGER NOT NULL,
    quantity      INTEGER DEFAULT 1,
    unit_sats     INTEGER NOT NULL,
    options_json  TEXT DEFAULT '{}',
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(id)
);

-- Rate limiting de login (para Fase 4+)
CREATE TABLE IF NOT EXISTS login_attempts (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    ip           TEXT NOT NULL,
    attempted_at TEXT DEFAULT (datetime('now'))
);
```

#### `models/model_products.py`

Funcoes CRUD para produtos. Todas usam `db.get_db()`.

```python
def get_all_products():
    """Retorna lista de dicts com produtos ativos, incluindo prices, images e options."""
    # SELECT de products WHERE active=1 ORDER BY sort_order
    # Para cada produto, buscar product_prices, product_images, product_options
    # Retornar no formato compativel com window.PRODUTOS (ver abaixo)

def get_product_by_id(product_id):
    """Retorna um unico produto com prices, images, options."""

def create_product(data):
    """Insere produto + prices + images + options. data e um dict."""

def update_product(product_id, data):
    """Atualiza produto existente. Substitui prices/images/options."""

def delete_product(product_id):
    """DELETE CASCADE remove produto e tudo relacionado."""

def products_to_js_format(products):
    """Converte lista de produtos do banco para o formato window.PRODUTOS.

    Formato esperado pelo JS existente:
    [
      {
        id: 'jade',
        nome: 'Jade DIY',
        imagens: ['images/jade1.png', ...],
        resumo: 'Carteira de hardware...',
        preco: [{ label: 'Jade DIY', valor: 'R$ 230' }, ...],
        detalhesHTML: '<h4>...</h4>',
        options: [{ type: 'colorPair', title: '...', inputs: [...] }, ...],
        allowAddOnSeed: true,
        buyButtonText: 'Comprar Jade DIY',
        badge: { text: 'Promo', variant: 'promo' }
      }
    ]

    Mapear:
    - products.name -> nome
    - products.summary -> resumo
    - products.details_html -> detalhesHTML
    - product_prices -> preco [{label, valor: display_text}]
    - product_images.filename -> imagens [filename, ...]
    - product_options -> options (parsear config_json para reconstruir)
    - products.allow_addon_seed -> allowAddOnSeed
    - products.buy_button_text -> buyButtonText
    - products.badge_text/badge_variant -> badge {text, variant}
    """
```

#### `scripts/seed_products.py`

Script para popular o banco a partir dos dados existentes.

O arquivo `js/produtos-data.js` contem 9 produtos em JavaScript. Como o arquivo nao e JSON puro, o script deve parsear os dados manualmente ou ter os dados hardcoded como dicts Python.

**Abordagem recomendada:** Hardcode os 9 produtos como lista de dicts Python no script seed, pois parsear JS com regex e fragil. Os dados estao em `/home/msi/sandlabs.store/static/js/produtos-data.js`.

Produtos atuais (IDs): `jade`, `pico`, `nerd`, `sandseed`, `krux`, `kruxcase`, `ttgo-case-bateria`, `jade-diy-sem-bateria`, `ttgo-case-sem-bateria`.

Cores atuais (de `static/js/config.js`): `amarelo`, `azul`, `laranja`, `preto`, `translucido`, `vermelho`.

**Nota sobre pricing dinamico:** `amount_sats` continua existindo para precos nativos em sats, mas precos fiat agora podem ser salvos com `pricing_mode='fiat'`, `currency_code` e `amount_fiat`. Nesses casos, carrinho e checkout resolvem o valor em sats no momento da compra. A UI do admin foi priorizada para `CHF` e `SATS`, mas a base ja aceita extensao futura para `USD`, `BRL`, `EUR` e outras moedas.

#### Alteracoes em `routes/routes_public.py`

Modificar as rotas `index` e `produtos` para:
1. Chamar `get_all_products()` do model
2. Converter para formato JS com `products_to_js_format()`
3. Serializar para JSON
4. Passar como variavel de contexto ao template

#### Alteracoes nos templates

Em `templates/index.html` e `templates/produtos.html`, substituir:
```html
<script src="{{ url_for('static', filename='js/produtos-data.js') }}"></script>
```
por:
```html
<script>window.PRODUTOS = {{ products_json|safe }};</script>
```

A variavel `products_json` vem do contexto do template (string JSON).

#### Alteracao em `app.py`

Adicionar `from init_db import init_db` e chamar `init_db()` antes de registrar blueprints.

### Verificacao

- Rodar `python scripts/seed_products.py` — banco populado
- Acessar `/` e `/produtos` — produtos renderizam identicos
- Verificar que `window.PRODUTOS` no HTML contem os mesmos dados

---

## Fase 3: Carrinho de Compras

**Objetivo:** Usuarios podem adicionar produtos ao carrinho, ajustar quantidades e ver resumo antes do checkout.

### Arquivos a criar

#### `models/model_cart.py`

```python
def get_cart(session_id, user_id=None):
    """Retorna itens do carrinho com detalhes do produto.
    Se user_id fornecido, busca por user_id. Senao, por session_id.
    Retorna lista de dicts:
    [{ id, product_id, product_name, price_label, display_text, amount_sats, quantity, options_json }]
    """

def add_to_cart(session_id, product_id, price_id, quantity, options_json, user_id=None):
    """Insere item no carrinho. Se ja existe (mesmo product_id + price_id + options), incrementa quantity."""

def update_cart_item(item_id, quantity):
    """Atualiza quantidade. Se quantity <= 0, remove o item."""

def remove_cart_item(item_id):
    """DELETE do item."""

def clear_cart(session_id, user_id=None):
    """Remove todos os itens do carrinho do usuario/sessao."""

def merge_cart(session_id, user_id):
    """Move itens do carrinho anonimo (session_id) para o usuario logado (user_id).
    Usado apos login. Se item ja existe no carrinho do user, soma quantidades."""

def get_cart_total(session_id, user_id=None):
    """Retorna total em sats de todos os itens."""

def get_cart_count(session_id, user_id=None):
    """Retorna numero total de itens (para badge no header)."""
```

#### `routes/routes_cart.py`

Blueprint `cart` com endpoints JSON:

```
POST /api/cart/add
  Body: { product_id, price_id, quantity, options: { color1: "amarelo", color2: "preto" } }
  Resposta: { ok: true, cart_count: N }

GET /api/cart
  Resposta: { items: [...], total_sats: N, count: N }

PUT /api/cart/<item_id>
  Body: { quantity: N }
  Resposta: { ok: true, cart_count: N }

DELETE /api/cart/<item_id>
  Resposta: { ok: true, cart_count: N }

DELETE /api/cart
  Resposta: { ok: true }

GET /carrinho
  Renderiza templates/cart.html com os itens do carrinho
```

**Nota sobre sessao:** Usar `session.sid` do Flask. Se nao existir, gerar um UUID e salvar na sessao. Exemplo:
```python
if "cart_session" not in session:
    session["cart_session"] = str(uuid.uuid4())
```

#### `templates/cart.html`

Pagina do carrinho estendendo `base.html`:
- Tabela/lista de itens com: nome do produto, opcoes selecionadas (cores), preco, quantidade (editavel), subtotal
- Botao remover por item
- Total geral em sats
- Botao "Finalizar compra" -> link para `/checkout`
- Botao "Continuar comprando" -> link para `/produtos`
- Estado vazio: mensagem "Seu carrinho esta vazio" + link para produtos

Usar o design system existente: classes `.card`, `.btn-accent`, `.btn-ghost`, `.glass`, etc.

#### `static/js/cart.js`

Novo arquivo JS para gerenciar o carrinho no frontend:

```javascript
// 1. Funcao addToCart(productId, priceId, quantity, options)
//    - Faz POST /api/cart/add via fetch
//    - Atualiza badge no header
//    - Mostra feedback visual (flash message ou toast)

// 2. Funcao updateCartBadge()
//    - Faz GET /api/cart e atualiza o numero no icone do carrinho no header

// 3. Na pagina do carrinho:
//    - Botoes +/- para quantidade -> PUT /api/cart/<id>
//    - Botao remover -> DELETE /api/cart/<id>
//    - Atualizar total ao mudar quantidade
```

#### Alteracoes em arquivos existentes

**`static/js/render-produtos.js`** (linhas 209-221):
Na funcao `openPurchaseModal`, a secao `final-actions` atualmente tem botoes WhatsApp e Telegram. Adicionar um terceiro botao "Adicionar ao Carrinho" ANTES dos botoes existentes:

```javascript
// Adicionar ANTES dos botoes WhatsApp/Telegram:
const bCart = el('button', { type:'button', class:'final-btn btn-accent' }, 'Adicionar ao Carrinho');
bCart.addEventListener('click', () => {
    // Coletar opcoes selecionadas do form
    // Chamar addToCart() de cart.js
    // Fechar modal
    // Mostrar feedback
});
actions.appendChild(bCart);
```

Os botoes WhatsApp/Telegram ficam como opcao secundaria (menor destaque).

**`templates/base.html`**:
Adicionar icone de carrinho no header (dentro do `<nav>`):
```html
<a class="nav-link" href="{{ url_for('cart.cart_page') }}" style="position:relative">
    Carrinho
    <span id="cart-badge" class="cart-badge" style="display:none">0</span>
</a>
```

Incluir `cart.js` no block scripts do base (ou como script global).

**CSS** (`static/css/style.css`):
Adicionar estilo para `.cart-badge`:
```css
.cart-badge {
    position: absolute;
    top: -6px; right: -10px;
    background: var(--accent);
    color: #fff;
    font-size: 0.7rem;
    padding: 2px 6px;
    border-radius: 10px;
    min-width: 18px;
    text-align: center;
}
```

#### Registrar blueprint no `app.py`

```python
from routes.routes_cart import cart
app.register_blueprint(cart)
```

### Verificacao

- Adicionar produto com cores ao carrinho -> badge atualiza
- Navegar entre paginas -> carrinho persiste
- Pagina `/carrinho` mostra itens corretos
- Alterar quantidade -> total atualiza
- Remover item -> item desaparece
- Carrinho vazio -> mensagem adequada

---

## Fase 4: Autenticacao de Usuarios

**Objetivo:** Registro, login, sessao persistente, merge de carrinho, controle de acesso admin.

### Arquivos a criar

#### `models/model_users.py`

```python
from werkzeug.security import generate_password_hash, check_password_hash

def create_user(email, password, display_name=""):
    """Insere usuario. Hash da senha com generate_password_hash(). Retorna user_id."""

def verify_user(email, password):
    """Busca usuario por email, verifica senha com check_password_hash().
    Retorna dict do usuario ou None."""

def get_user_by_id(user_id):
    """SELECT por id."""

def get_user_by_email(email):
    """SELECT por email."""

def is_rate_limited(ip):
    """Conta tentativas de login do IP nos ultimos 15 minutos.
    Retorna True se >= 5 tentativas."""

def record_login_attempt(ip):
    """INSERT em login_attempts."""

def cleanup_old_attempts():
    """DELETE de tentativas com mais de 15 minutos."""
```

#### `routes/routes_auth.py`

Blueprint `auth`:

```
GET  /auth/login       -> render login.html
POST /auth/login       -> verificar credenciais, rate limit, criar sessao
                          Se user tinha carrinho anonimo, chamar merge_cart()
                          Redirect para / ou para url anterior (next param)

GET  /auth/register    -> render register.html
POST /auth/register    -> criar usuario, logar automaticamente, merge_cart
                          Redirect para /

POST /auth/logout      -> limpar sessao, redirect para /
```

**CSRF:** Todas as rotas POST devem validar `csrf_token`. Portar a logica de CSRF do FREESANDMANN:

```python
# Em app.py ou num modulo app_hooks.py:
CSRF_EXEMPT = set()  # Adicionar paths de webhooks depois

@app.before_request
def generate_csrf_token():
    if "csrf_token" not in session:
        session["csrf_token"] = os.urandom(16).hex()

@app.before_request
def csrf_protect():
    if request.method == "POST":
        if request.path in CSRF_EXEMPT:
            return
        token = session.get("csrf_token", "")
        form_token = request.form.get("csrf_token", "") or request.headers.get("X-CSRFToken", "")
        if not token or token != form_token:
            abort(403)
```

**Fonte:** `/home/msi/FREESANDMANN/app_hooks.py` linhas 60-81.

**Security headers:** Portar do FREESANDMANN (`app_hooks.py` linhas 84-91):
```python
@app.after_request
def set_security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    if not app.debug:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response
```

#### Decorators de acesso

```python
from functools import wraps
from flask import session, redirect, url_for, abort

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("auth.login", next=request.url))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("auth.login", next=request.url))
        if not session.get("is_admin"):
            abort(403)
        return f(*args, **kwargs)
    return decorated
```

#### `routes/routes_account.py`

Blueprint `account` (requer `login_required`):

```
GET /account/orders           -> lista de pedidos do usuario
GET /account/orders/<id>      -> detalhe do pedido (status, tracking, itens)
```

#### Templates

**`templates/auth/login.html`** — Form com email + senha + csrf_token + botao login + link para registro.
**`templates/auth/register.html`** — Form com nome, email, senha, confirmar senha + csrf_token.
**`templates/account/orders.html`** — Lista de pedidos com status (badge colorido por status).
**`templates/account/order_detail.html`** — Detalhe: itens, precos, status, tracking, datas.

Todos usando o design system existente (`.card`, `.glass`, `.btn-accent`, tema dark).

#### Admin inicial

No `init_db.py`, apos criar tabelas, verificar se existe admin:
```python
if config.ADMIN_PASSWORD:
    # Criar usuario admin bootstrap se nao existe
    # email: config.ADMIN_USERNAME + "@admin.local"
    # is_admin: 1
    # marcar setup_complete=1 no config
```

Se `ADMIN_PASSWORD` estiver vazio, o fluxo padrao agora e:

- qualquer rota `/admin/*` redireciona para `/admin/setup` enquanto nao existir admin
- `/admin/setup` cria o primeiro admin, define a senha e inicia a sessao automaticamente
- o wizard pode opcionalmente salvar `coinos_api_key`, `coinos_webhook_secret` e `coinos_enabled`

#### Alteracoes no `templates/base.html`

Adicionar no nav, apos o carrinho:
```html
{% if session.user_id %}
    <a class="nav-link" href="{{ url_for('account.orders') }}">Pedidos</a>
    <a class="nav-link" href="{{ url_for('auth.logout') }}">Sair</a>
{% else %}
    <a class="nav-link" href="{{ url_for('auth.login') }}">Entrar</a>
{% endif %}
```

### Verificacao

- Registrar usuario -> logado automaticamente
- Login -> sessao criada, carrinho anonimo migrado
- Logout -> sessao limpa
- 5 tentativas de login erradas do mesmo IP -> bloqueado 15min
- Acessar /account/orders sem login -> redirect para login
- CSRF token invalido -> 403

---

## Fase 5: Pagamento Lightning via Coinos

**Objetivo:** Checkout completo com criacao de invoice Lightning e confirmacao automatica.

### Codigo de referencia do FREESANDMANN

Os seguintes arquivos devem ser adaptados (NAO copiados literalmente):

- **`/home/msi/FREESANDMANN/coinos_client.py`** -> `services/service_coinos.py`
- **`/home/msi/FREESANDMANN/service_qr.py`** -> `services/service_qr.py`
- **`/home/msi/FREESANDMANN/service_donations.py`** -> logica integrada em `routes/routes_checkout.py`

### `services/service_coinos.py`

Adaptar de `/home/msi/FREESANDMANN/coinos_client.py`. Mudancas:

1. **API key:** Ler de `models/model_config.py` (`get_config("coinos_api_key")`) com fallback para `config.COINOS_API_KEY`
2. **Webhook secret:** Ler de `models/model_config.py` (`get_config("coinos_webhook_secret")`) com fallback para `config.COINOS_WEBHOOK_SECRET`
3. **Enabled check:** Usar `get_bool_config("coinos_enabled")` com fallback para `config.COINOS_ENABLED`
4. **Remover:** `get_received_sats()`, `check_lightning_balance()`, `get_onchain_address()`, `get_fresh_*_address()`, `get_account_username()`, `_coinos_public_request()` — funcoes especificas de balance tracking de doacoes
5. **Manter:** `_coinos_request()`, `create_invoice()`, `check_invoice()`

Estrutura final:
```python
"""Coinos.io API client for sandlabs.store"""
import json, logging, re, urllib.request
import config
from models.model_config import get_config, get_bool_config

COINOS_API_BASE = "https://coinos.io/api"
_COINOS_HASH_PATTERN = re.compile(r"^[a-zA-Z0-9]+$")

def _coinos_request(method, path, body=None):
    api_key = get_config("coinos_api_key", config.COINOS_API_KEY)
    if not api_key:
        return None
    # ... resto identico ao FREESANDMANN ...

def create_invoice(amount_sats, invoice_type="lightning", webhook_url=None):
    if not get_bool_config("coinos_enabled", config.COINOS_ENABLED):  # <-- mudanca
        return None
    # ... validacoes identicas ...
    invoice_data = {"amount": amount_sats, "type": invoice_type}
    if webhook_url:
        secret = get_config("coinos_webhook_secret", config.COINOS_WEBHOOK_SECRET)
        if secret:
            invoice_data["secret"] = secret
        invoice_data["webhook"] = webhook_url
    return _coinos_request("POST", "/invoice", {"invoice": invoice_data})

def check_invoice(invoice_hash):
    # ... identico ao FREESANDMANN ...
```

### `services/service_qr.py`

Adaptar de `/home/msi/FREESANDMANN/service_qr.py`. Simplificar:

```python
"""QR code generation for Lightning invoices."""
import io
import qrcode
from flask import send_file

def get_invoice_qr_response(bolt11):
    """Gera PNG com QR code do BOLT11. Retorna Flask response ou None."""
    if not bolt11 or len(bolt11) > 2000:
        return None
    img = qrcode.make(bolt11, box_size=8, border=2)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return send_file(buf, mimetype="image/png", max_age=60)
```

### `models/model_orders.py`

```python
def create_order(user_id, session_id, items, shipping_info, total_sats, shipping_sats, coupon_code=None):
    """Cria pedido + order_items a partir dos itens do carrinho.
    items: lista de dicts do carrinho (product_id, price_id, quantity, unit_sats, options_json)
    shipping_info: dict com name, address, postal_code, country
    Retorna order_id."""

def set_order_payment(order_id, invoice_hash, bolt11):
    """Atualiza pedido com dados da invoice Coinos."""

def confirm_order_payment(order_id):
    """Marca pedido como 'paid', seta payment_confirmed_at = now()."""

def update_order_status(order_id, status):
    """Atualiza status (processing, shipped, delivered, cancelled)."""

def set_order_tracking(order_id, tracking_code):
    """Seta shipping_tracking."""

def get_order(order_id):
    """Retorna pedido com order_items."""

def get_orders_by_user(user_id):
    """Lista pedidos do usuario, ORDER BY created_at DESC."""

def get_all_orders(status_filter=None):
    """Lista todos os pedidos (admin). Filtro opcional por status."""
```

### `routes/routes_checkout.py`

Blueprint `checkout`:

```
GET /checkout
    - Requer itens no carrinho (senao redirect para /carrinho)
    - Renderiza checkout.html com: itens, total, form de endereco

POST /checkout/create-order
    Body (form): name, address, postal_code, country, csrf_token
    1. Validar form
    2. Calcular shipping (service_shipping, Fase 6 — se nao implementado ainda, shipping=0)
    3. Criar order no banco (model_orders.create_order)
    4. Criar invoice Coinos (service_coinos.create_invoice)
       - amount = total_sats + shipping_sats
       - webhook_url = request.url_root + url_for('checkout.coinos_webhook')
    5. Salvar invoice no order (model_orders.set_order_payment)
    6. Limpar carrinho
    7. Redirect para GET /checkout/payment/<order_id>

GET /checkout/payment/<order_id>
    - Renderiza payment.html com: QR code URL, BOLT11, amount, status
    - JS faz polling

GET /api/checkout/check-payment/<order_id>
    - Buscar order no banco
    - Se ja confirmado, retornar { paid: true }
    - Senao, chamar service_coinos.check_invoice(order.invoice_hash)
    - Se received > 0: chamar confirm_order_payment(), retornar { paid: true }
    - Senao: retornar { paid: false }

GET /checkout/invoice-qr
    Query: bolt11=lnbc...
    - Chamar service_qr.get_invoice_qr_response(bolt11)
    - Retornar imagem PNG

POST /checkout/webhook/coinos   (CSRF EXEMPT)
    - Validar webhook secret
    - Extrair hash e received do body JSON
    - Se received > 0: buscar order por invoice_hash, confirmar pagamento
    - Retornar { ok: true }
```

**CSRF exemption:** Adicionar `/checkout/webhook/coinos` ao set `CSRF_EXEMPT`.

### `static/js/payment.js`

Polling de pagamento (adaptar logica de `/home/msi/FREESANDMANN/static/app.js` linhas 228-242):

```javascript
(function(){
    var container = document.getElementById('payment-container');
    if (!container) return;

    var checkUrl = container.dataset.checkUrl;    // /api/checkout/check-payment/<order_id>
    var successUrl = container.dataset.successUrl; // /account/orders/<order_id>
    var status = document.getElementById('payment-status');
    var pollInterval = 2000;

    var timer = setInterval(function(){
        fetch(checkUrl)
        .then(function(r){ return r.json(); })
        .then(function(data){
            if (data.paid) {
                clearInterval(timer);
                status.textContent = 'Pagamento confirmado!';
                status.className = 'invoice-status invoice-paid';
                setTimeout(function(){
                    window.location.href = successUrl;
                }, 2000);
            }
        });
    }, pollInterval);

    // Copiar BOLT11
    var copyBtn = document.getElementById('copy-bolt11');
    if (copyBtn) {
        copyBtn.addEventListener('click', function(){
            var bolt11 = document.getElementById('bolt11-text').textContent;
            navigator.clipboard.writeText(bolt11);
            copyBtn.textContent = 'Copiado!';
            setTimeout(function(){ copyBtn.textContent = 'Copiar'; }, 2000);
        });
    }
})();
```

### Templates

**`templates/checkout.html`** — Form com campos de envio (nome, endereco, CEP, pais), resumo do pedido, total em sats, botao "Pagar com Lightning".

**`templates/payment.html`** — QR code grande, BOLT11 com botao copiar, "Aguardando pagamento..." animado, auto-redirect ao confirmar. Incluir `payment.js`.

### Fluxo completo

```
Usuario no /carrinho -> clica "Finalizar"
-> GET /checkout (form de endereco)
-> POST /checkout/create-order (cria pedido + invoice)
-> GET /checkout/payment/<id> (QR + polling)
-> [usuario paga via wallet Lightning]
-> GET /api/checkout/check-payment/<id> retorna { paid: true }
-> JS redireciona para /account/orders/<id>
-> Webhook tambem confirma (redundancia)
```

### Verificacao

- Criar pedido a partir do carrinho -> order no banco
- Invoice Coinos criada com amount correto
- QR code exibe invoice valida
- Polling detecta pagamento (testar com invoice de 1 sat na testnet ou Coinos sandbox)
- Order status atualiza para "paid"
- Webhook funciona como backup
- Carrinho limpo apos criar pedido

---

## Fase 6: Calculo de Frete Post.ch

**Objetivo:** Calcular custo de envio e converter para sats.

### `services/service_shipping.py`

Abordagem: tabela de precos estatica dos Correios Suicos (Post.ch), editavel via admin. A API oficial Post.ch requer contrato empresarial, entao usamos lookup table.

```python
"""Swiss Post shipping cost calculator."""
import json
import db

# Precos padrao PostPac (CHF) — atualizaveis via tabela config no banco
DEFAULT_RATES = {
    "CH": {2: 7.00, 10: 9.50, 30: 16.00},           # Domestico Suica
    "EU": {2: 20.00, 5: 30.00, 10: 45.00, 30: 80.00},   # Europa
    "WORLD": {2: 30.00, 5: 50.00, 10: 75.00, 30: 120.00} # Resto do mundo
}

# Mapeamento de paises para zonas
EU_COUNTRIES = {
    "AT","BE","BG","HR","CY","CZ","DK","EE","FI","FR","DE","GR","HU",
    "IE","IT","LV","LT","LU","MT","NL","PL","PT","RO","SK","SI","ES","SE",
    "NO","IS","LI","GB"
}

def get_country_zone(country_code):
    """Retorna zona: 'CH', 'EU' ou 'WORLD'."""
    cc = (country_code or "").upper().strip()
    if cc == "CH":
        return "CH"
    if cc in EU_COUNTRIES:
        return "EU"
    return "WORLD"

def get_shipping_rates():
    """Busca tabela de frete do banco (config key 'shipping_rates').
    Retorna DEFAULT_RATES se nao configurado."""
    conn = db.get_db()
    row = conn.execute("SELECT value FROM config WHERE key='shipping_rates'", []).fetchone()
    conn.close()
    if row:
        try:
            return json.loads(row["value"])
        except (json.JSONDecodeError, TypeError):
            pass
    return DEFAULT_RATES

def calculate_shipping_chf(weight_grams, country_code):
    """Calcula frete em CHF baseado no peso e destino.
    Retorna o preco da faixa de peso correspondente."""
    zone = get_country_zone(country_code)
    rates = get_shipping_rates()
    zone_rates = rates.get(zone, rates.get("WORLD", {}))

    weight_kg = weight_grams / 1000.0
    # Encontrar a faixa de peso correspondente
    for max_kg in sorted(zone_rates.keys(), key=lambda x: float(x)):
        if weight_kg <= float(max_kg):
            return zone_rates[max_kg]

    # Acima de todas as faixas: usar a maior
    if zone_rates:
        return zone_rates[max(zone_rates.keys(), key=lambda x: float(x))]
    return 0.0
```

### `services/service_btc_price.py`

Conversao BTC/CHF em tempo real para calcular frete em sats.

```python
"""BTC/CHF price feed for shipping cost conversion."""
import json, time, logging, urllib.request

logger = logging.getLogger(__name__)

_cache = {"rate": None, "timestamp": 0}
CACHE_TTL = 300  # 5 minutos

COINGECKO_URL = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=chf"

def get_btc_chf_rate():
    """Retorna preco atual de 1 BTC em CHF. Usa cache de 5 minutos."""
    now = time.time()
    if _cache["rate"] and (now - _cache["timestamp"]) < CACHE_TTL:
        return _cache["rate"]

    try:
        req = urllib.request.Request(COINGECKO_URL)
        req.add_header("Accept", "application/json")
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            rate = data["bitcoin"]["chf"]
            _cache["rate"] = rate
            _cache["timestamp"] = now
            return rate
    except Exception:
        logger.exception("Failed to fetch BTC/CHF rate")
        return _cache["rate"]  # fallback para ultimo valor conhecido

def chf_to_sats(amount_chf):
    """Converte valor em CHF para satoshis."""
    rate = get_btc_chf_rate()
    if not rate or rate <= 0:
        return 0
    btc_amount = amount_chf / rate
    return int(btc_amount * 100_000_000)
```

### Endpoint de calculo

Adicionar em `routes/routes_checkout.py`:

```
POST /api/shipping/calculate
    Body: { country: "CH", weight_grams: 350 }
    Resposta: { shipping_chf: 7.00, shipping_sats: 8500, zone: "CH" }
```

### Integracao no checkout

No template `checkout.html`, quando o usuario seleciona o pais:
1. JS calcula peso total dos itens do carrinho (cada produto tem `weight_grams`)
2. Faz POST `/api/shipping/calculate` com pais + peso
3. Mostra custo do frete em CHF e sats
4. Atualiza total do pedido (produtos + frete)

No `POST /checkout/create-order`, calcular frete server-side e incluir no `shipping_sats` do pedido.

### Campo weight_grams nos produtos

O schema ja inclui `weight_grams` (adicionado na Fase 2). Pesos aproximados para seed dos produtos:

| Produto | Peso (g) |
|---------|----------|
| jade | 150 |
| pico | 50 |
| nerd | 100 |
| sandseed | 200 |
| krux | 250 |
| kruxcase | 100 |
| ttgo-case-bateria | 150 |
| jade-diy-sem-bateria | 100 |
| ttgo-case-sem-bateria | 80 |

### Verificacao

- POST /api/shipping/calculate com CH -> retorna ~7 CHF
- POST com DE (Alemanha) -> zona EU -> ~20 CHF
- POST com BR (Brasil) -> zona WORLD -> ~30 CHF
- Valores em sats correspondem a taxa BTC/CHF atual
- Checkout inclui frete no total
- Admin pode editar tabela de frete (Fase 7)

---

## Fase 7: Painel Admin

**Objetivo:** Interface server-side para gerenciar produtos, pedidos, pagamentos e configuracoes.

### `routes/routes_admin.py`

Blueprint `admin`, todas as rotas protegidas com `admin_required`.

```
GET /admin
    Dashboard: cards com metricas
    - Total pedidos (por status)
    - Receita total em sats (soma de orders.total_sats WHERE status IN ('paid','processing','shipped','delivered'))
    - Pedidos pendentes de envio (status='paid' ou 'processing')
    - Tabela com ultimos 10 pedidos

GET /admin/products
    Lista de todos os produtos (ativos e inativos)
    Botao "Novo produto"
    Para cada produto: nome, preco principal, badge, botoes editar/desativar

GET /admin/products/new
POST /admin/products/new
    Formulario de criacao de produto
    Campos: id (slug), nome, resumo, detalhes_html, peso, buy_button_text, allow_addon_seed, badge
    Precos: lista dinamica (label + currency_code + amount_sats/amount_fiat + preview)
    Opcoes: lista dinamica (tipo + config JSON)
    Upload de imagens: multiplos arquivos PNG
    Ao salvar: INSERT no banco + salvar imagens em static/images/ + gerar thumbnail (se Fase 8 implementada)

GET /admin/products/<id>/edit
POST /admin/products/<id>/edit
    Mesmo formulario, pre-preenchido
    Ao salvar: UPDATE + substituir precos/opcoes/imagens

POST /admin/products/<id>/delete
    Soft delete (active=0) ou hard delete (DELETE CASCADE)

GET /admin/orders
    Lista de todos os pedidos
    Filtros: status dropdown, busca por email/nome
    Colunas: ID, data, cliente, total sats, status (badge colorido), acoes

GET /admin/orders/<id>
    Detalhe: dados do cliente, endereco, itens com opcoes, pagamento (hash, status), tracking
    Botoes de acao: marcar como "processing", "shipped" (com campo tracking), "delivered", "cancelled"

POST /admin/orders/<id>/status
    Body: { status, tracking? }
    Atualiza status do pedido

GET /admin/settings
POST /admin/settings
    Formulario com:
    - Coinos API Key (password field)
    - Coinos Webhook Secret
    - Coinos Enabled (toggle)
    - Tabela de frete (JSON editavel ou formulario estruturado por zona)
    - Contatos WhatsApp/Telegram
```

### Templates admin

Todos estendem `templates/admin/base_admin.html` que estende `base.html` e adiciona sidebar/nav admin.

Design: usar o mesmo tema dark/glassmorphism. Formularios com inputs estilizados (similar ao `config.html` existente).

### Upload de imagens

No formulario de produto:
```html
<input type="file" name="product_images" multiple accept="image/png,image/jpeg,image/webp">
```

No handler:
```python
from werkzeug.utils import secure_filename
import os

UPLOAD_DIR = os.path.join(app.static_folder, "images")

for file in request.files.getlist("product_images"):
    filename = secure_filename(file.filename)
    filepath = os.path.join(UPLOAD_DIR, filename)
    file.save(filepath)
    # INSERT em product_images
    # Se Fase 8: gerar thumbnail automaticamente
```

### Registrar blueprint

```python
from routes.routes_admin import admin
app.register_blueprint(admin)
```

### Verificacao

- Admin loga -> ve dashboard com metricas
- Criar produto -> aparece na loja
- Editar produto -> mudancas refletem
- Upload imagem -> imagem acessivel na galeria
- Listar pedidos -> filtrar por status
- Marcar pedido como shipped com tracking -> status atualiza
- Editar configuracoes -> valores salvos

---

## Fase 8: Otimizacao de Imagens

**Objetivo:** Reducir peso da pagina de ~31MB para ~1-2MB gerando thumbnails comprimidos.

### `services/service_images.py`

```python
"""Image optimization: thumbnail generation via Pillow."""
import os
from PIL import Image

THUMB_DIR = "thumb"
FULL_DIR = "full"
THUMB_MAX_WIDTH = 400
THUMB_QUALITY = 80

def get_images_base_dir(app):
    return os.path.join(app.static_folder, "images")

def generate_thumbnail(source_path, dest_path, max_width=THUMB_MAX_WIDTH, quality=THUMB_QUALITY):
    """Redimensiona imagem para max_width e salva como WebP."""
    img = Image.open(source_path)
    if img.width > max_width:
        ratio = max_width / img.width
        new_size = (max_width, int(img.height * ratio))
        img = img.resize(new_size, Image.LANCZOS)
    img.save(dest_path, format="WEBP", quality=quality)

def ensure_thumbnail(base_dir, filename):
    """Gera thumbnail se nao existe. Retorna path relativo do thumb."""
    full_path = os.path.join(base_dir, filename)
    if not os.path.exists(full_path):
        return filename  # fallback para original

    # thumb path: trocar extensao para .webp e colocar em thumb/
    name = os.path.splitext(os.path.basename(filename))[0]
    thumb_filename = f"thumb/{name}.webp"
    thumb_path = os.path.join(base_dir, thumb_filename)

    if not os.path.exists(thumb_path):
        os.makedirs(os.path.dirname(thumb_path), exist_ok=True)
        generate_thumbnail(full_path, thumb_path)

    return thumb_filename
```

### `scripts/generate_thumbnails.py`

Script para gerar todos os thumbnails em batch:

```python
"""Gera thumbnails para todas as imagens em static/images/."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from services.service_images import generate_thumbnail

IMAGES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "images")
THUMB_DIR = os.path.join(IMAGES_DIR, "thumb")

os.makedirs(THUMB_DIR, exist_ok=True)

for fname in os.listdir(IMAGES_DIR):
    if fname.lower().endswith(('.png', '.jpg', '.jpeg')):
        source = os.path.join(IMAGES_DIR, fname)
        name = os.path.splitext(fname)[0]
        dest = os.path.join(THUMB_DIR, f"{name}.webp")
        if not os.path.exists(dest):
            generate_thumbnail(source, dest)
            print(f"  {fname} -> thumb/{name}.webp")
        else:
            print(f"  {fname} (thumb existe)")
```

### Migracao de imagens

1. Mover imagens originais: `static/images/*.png` -> `static/images/full/`
2. Gerar thumbnails: `static/images/thumb/*.webp`
3. Manter backwards compatibility: os paths no banco (`images/jade1.png`) continuam funcionando

**Alternativa mais simples (recomendada):** NAO mover imagens para `full/`. Manter na raiz de `images/` e gerar thumbnails em `images/thumb/`. O lightbox usa o path original, a galeria usa `thumb/`.

### Alteracoes no JS

Modificar `static/js/render-produtos.js` funcao `buildGallery()` (linhas 23-43):

```javascript
function buildGallery(prod) {
    const g = el('div', { class:'galeria' });
    const fullPaths = prod.imagens.map(src => src);
    prod.imagens.forEach((src, i) => {
        // Gerar path do thumbnail: images/jade1.png -> images/thumb/jade1.webp
        const thumbSrc = src.replace(/^(images\/)(.+)\.\w+$/, '$1thumb/$2.webp');
        const img = el('img', {
            src: thumbSrc,                // <-- thumbnail para galeria
            alt: `${prod.nome} ${i + 1}`,
            loading: 'lazy',
            decoding: 'async',
            sizes: '(min-width:1200px) 300px, (min-width:768px) 33vw, 50vw'
        });
        img.addEventListener('click', () => {
            if (window.lightbox && typeof lightbox.open === 'function') {
                lightbox.open(fullPaths, i);  // <-- full quality no lightbox
            }
        });
        g.appendChild(img);
    });
    return g;
}
```

Mesma logica para `render-home.js` na funcao `buildCard()` (linha 26): usar thumbnail no card.

### Impacto esperado

| Imagem | Original PNG | Thumbnail WebP |
|--------|-------------|----------------|
| jade1.png | ~345 KB | ~15-25 KB |
| produto.png | ~481 KB | ~20-30 KB |
| Maiores (>1MB) | 1-7 MB | ~25-40 KB |
| **Total pagina** | **~31 MB** | **~1-2 MB** |

### Verificacao

- Rodar `python scripts/generate_thumbnails.py` -> thumbnails criados
- Galeria usa thumbnails (verificar no Network tab do browser)
- Lightbox abre imagem original full quality
- Cards na home usam thumbnails
- Tempo de carregamento significativamente menor

---

## Fase 9: Polish e Producao

**Objetivo:** Ajustes finais de UX, SEO, seguranca e deploy.

### Tarefas

1. **Flash messages** — Adicionar ao `base.html`:
   ```html
   {% with messages = get_flashed_messages(with_categories=true) %}
   {% if messages %}
   <div class="flash-container">
       {% for category, message in messages %}
       <div class="flash flash-{{ category }}">{{ message }}</div>
       {% endfor %}
   </div>
   {% endif %}
   {% endwith %}
   ```
   CSS para `.flash`, `.flash-success`, `.flash-error` no estilo glassmorphism.

2. **Endpoint /health** — Para Docker healthcheck:
   ```python
   @app.route("/health")
   def health():
       return {"status": "ok"}, 200
   ```

3. **SEO** — Adicionar no `base.html`:
   ```html
   <meta name="description" content="Hardware wallets Bitcoin open source">
   <meta property="og:title" content="Sandlabs — {{ block title }}">
   <meta property="og:description" content="Hardware wallets e acessórios Bitcoin">
   <meta property="og:image" content="{{ url_for('static', filename='images/logo.png') }}">
   ```

4. **Logging estruturado** — Ja configurado basico em `app.py`. Adicionar logs em rotas criticas (checkout, pagamento, admin).

5. **Dockerfile producao** — Multi-stage build, usuario non-root:
   ```dockerfile
   RUN adduser --disabled-password --gecos '' appuser
   USER appuser
   ```

6. **Docker healthcheck**:
   ```dockerfile
   HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
       CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"
   ```

7. **Precos em sats** — Exibir preco em sats ao lado do preco em BRL usando `service_btc_price.py`.

8. **Limpar arquivos legados** — Apos todas as fases, remover os HTMLs originais da raiz (index.html, produtos.html, etc.) e os diretorios css/, js/, images/ da raiz (agora estao em static/).

### Verificacao final end-to-end

1. Navegar pelo site -> paginas carregam rapido (thumbnails)
2. Adicionar produto ao carrinho com cores selecionadas
3. Ir para checkout -> inserir endereco -> frete calculado
4. Pagar com Lightning -> QR code -> pagamento confirmado
5. Ver pedido em /account/orders
6. Admin: ver pedido, marcar como shipped com tracking
7. Usuario: ver tracking atualizado

---

## Dependencias entre Fases

```
Fase 1 (Flask Skeleton) ........... COMPLETA
  |
  v
Fase 2 (Database + Produtos) ...... COMPLETA
  |
  +---> Fase 3 (Carrinho) [COMPLETA] ---> Fase 4 (Auth) [COMPLETA] ---> Fase 5 (Pagamento) [COMPLETA] ---> Fase 6 (Frete) [COMPLETA]
  |
  +---> Fase 7 (Admin) [COMPLETA]
  |
  +---> Fase 8 (Imagens) [COMPLETA]

Fase 9 (Polish) [COMPLETA]
```

**Fases que podem ser executadas em paralelo:**
- Fase 7 + Fase 8 (apos Fase 2)
- Fase 3 e Fase 8 (apos Fase 2)

**Fases estritamente sequenciais:**
- Fase 3 -> Fase 4 -> Fase 5 -> Fase 6

---

## Regras de Workflow para Agentes

### 1. Testes devem ser executados por um agente de menor custo

Apos cada fase ou alteracao significativa, os testes automatizados devem ser executados por um **subagente mais barato** (ex: Claude Haiku, `subagent_type: "general-purpose"` com `model: "haiku"`). Isso reduz custo sem sacrificar validacao.

```bash
python -m pytest tests/ -v
```

O agente principal (Opus/Sonnet) **nao deve gastar tokens rodando testes** — deve delegar para o subagente barato.

### 2. Gate de fase: testes devem passar antes de avancar

Uma fase so e considerada **completa** e a proxima fase so pode **iniciar** quando:

- Todos os testes existentes passam com **0 falhas** (`python -m pytest tests/ -v`)
- Novos testes foram adicionados para cobrir a funcionalidade da fase recem-implementada
- O resultado do pytest e reportado ao usuario

Se algum teste falhar, o agente deve **corrigir o codigo** ate que todos passem antes de prosseguir.

### 3. Commit git obrigatorio por fase

Cada fase ou bloco relevante de alteracoes deve ser finalizado com um **commit git separado** usando o git do usuario:

```bash
git add <arquivos relevantes>
git commit -m "Fase N: descricao curta do que foi feito"
```

**Regras:**
- Mensagem de commit descritiva, indicando a fase e o que mudou
- Nunca acumular multiplas fases em um unico commit
- Apos o commit, atualizar este `ARCHITECTURE.md` para registrar o hash do commit e marcar a fase como completa
- O commit so deve ser feito **apos os testes passarem** (regra 2)

### Resumo do fluxo por fase

```
1. Implementar codigo da fase N
2. Escrever/atualizar testes para fase N
3. Delegar execucao de testes para subagente barato (Haiku)
4. Se falhou: corrigir → voltar ao passo 3
5. Se passou: git commit com mensagem descritiva
6. Atualizar ARCHITECTURE.md (hash do commit, estado da fase)
7. Iniciar fase N+1
```

---

## Convencoes de Codigo

- **Models:** Funcoes puras que recebem parametros e usam `db.get_db()` internamente. Fechar conexao apos uso.
- **Routes:** Blueprints Flask. Usar `jsonify()` para APIs, `render_template()` para paginas.
- **Services:** Logica de negocio sem dependencia de Flask (exceto service_qr que usa send_file).
- **Templates:** Herdar de `base.html`. Usar blocks `title`, `content`, `scripts`, `footer`.
- **CSS:** NAO modificar `style.css` existente exceto para ADICIONAR novas classes. Usar design tokens existentes.
- **JS:** Manter arquivos existentes funcionando. Novos arquivos em `static/js/`.
- **Nomes de arquivo:** `model_*.py`, `routes_*.py`, `service_*.py` — consistente com FREESANDMANN.
