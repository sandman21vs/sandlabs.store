# Sandlabs.store

Este projeto é uma loja open-source voltada para a venda de produtos relacionados ao universo Bitcoin. Você pode copiar e usar este repositório para criar sua própria loja Bitcoinheira.

## Requisitos para Instalação

Para instalar este site em seu próprio node, siga as etapas abaixo:

1. Instale o **Portainer**.
2. Configure o **Cloudflare Tunnel**.
3. Coloque todos os arquivos em uma imagem **Nginx**.

> **Nota**: Em breve, fornecerei tutoriais mais completos para facilitar o processo de instalação.

## Personalização

Antes de usar este repositório em sua própria loja, **remova todas as imagens pessoais (logo), nome e contatos** que possam dar a entender que eu tenha qualquer relação com você ou com sua loja.

## Licença

Este projeto está licenciado sob a **Licença GPLv3**.

---

Seja bem-vindo ao mercado aberto e livre do Bitcoin! Divirta-se e respeite sempre seus clientes.

--- 

Em caso de dúvidas ou sugestões, entre em contato com a comunidade ou contribua para melhorar este projeto.



# Sandlabs.store

Loja open-source para vender hardware/peças relacionadas a Bitcoin. Você pode **clonar e adaptar** este repositório para sua própria loja.

---

## 📁 Estrutura do projeto

```
/
├─ index.html            # Home (lista os produtos dinamicamente)
├─ produtos.html         # Página de produtos (render dinâmico + modais)
├─ sobre.html            # Página institucional
├─ termos.html           # Pagamentos/privacidade/envio
├─ suporte.html          # Canais de contato
├─ css/
│  └─ style.css          # Estilos, tokens e layout (inclui hero com fundo orgânico)
├─ js/
│  ├─ produtos-data.js   # 🔑 Catálogo de produtos (único lugar para editar/novos itens)
│  ├─ render-home.js     # Renderiza cards dos produtos na home
│  ├─ render-produtos.js # Renderiza seções, galerias e modais em /produtos.html
│  ├─ compras.js         # Finalização (WhatsApp/Telegram) 100% guiada pelo produtos-data.js
│  └─ cupom.js           # Propaga ?cupom=... entre páginas/inputs
└─ images/
   ├─ logo.png           # Logo da loja
   ├─ produto.png        # Imagem de fundo do herói (home)
   └─ ...                # Demais imagens do catálogo
```

> **Resumo importante:** Para **adicionar/editar produtos**, altere **_apenas_** `js/produtos-data.js`. O restante (home, página de produtos e finalização de compra) se adapta automaticamente.

---

## 🚀 Deploy

### Opção 1 — Docker com Nginx (nginx:latest)
- O `Dockerfile` usa `nginx:latest`, copia o repositório para `/usr/share/nginx/html` e expõe essa pasta como volume.
- Com o bind mount, editar os arquivos locais reflete direto no container:
```bash
docker build -t sandlabs-site .
docker run -d --name sandlabs-site -p 8080:80 \
  -v "$(pwd)":/usr/share/nginx/html \
  sandlabs-site
```
- Se preferir a imagem fechada (sem bind), remova o `-v` e recrie o container a cada mudança.
- Atualização automática opcional:
  - A imagem instala `git` e `rsync` e usa `/entrypoint.sh` para sincronizar o conteúdo antes de subir o Nginx.
  - Defina `REPO_URL` (ex.: `https://github.com/seuuser/sandlabs.store.git`) e, opcionalmente, `REPO_BRANCH` (padrão `main`). Exemplo:
  ```bash
  docker run -d --name sandlabs-site -p 8080:80 \
    -e REPO_URL=https://github.com/seuuser/sandlabs.store.git \
    -e REPO_BRANCH=main \
    -v "$(pwd)":/usr/share/nginx/html \
    sandlabs-site
  ```
  - Para desativar a checagem: `-e AUTO_UPDATE=false`.

### Opção 2 — Nginx instalado no host (sem Docker)
1) Instale Nginx (ex.: `sudo apt install nginx`).  
2) Limpe a pasta pública (ex.: `/var/www/html` ou `/usr/share/nginx/html`):  
   `sudo rm -rf /var/www/html/*`  
3) Copie o conteúdo do repositório para lá:  
   `sudo cp -r . /var/www/html`  
4) Garanta que o site está servindo na porta 80 (server block padrão do Nginx já atende).  
5) Sempre que editar o site, copie os arquivos novamente ou use um deploy/rsync.

> Para teste rápido local sem Nginx: `python -m http.server 8080` e acesse http://localhost:8080

---

## 🛠️ Painel web de configuração (config.html)

- A página não aparece no menu; acesse diretamente `/config.html` (admins).
- Edite **contatos (Whats/Telegram)** e o catálogo (JSON de `js/produtos-data.js`) via interface.
- **Salvar** grava no `localStorage` do navegador atual (só vale para quem usou o painel).
- **Exportar produtos-data.js** baixa um arquivo já atualizado; substitua `js/produtos-data.js` no host ou dentro do container/volume.
  - Docker com bind mount: basta salvar o arquivo exportado sobre `js/produtos-data.js` na pasta montada.
  - Docker sem bind/host: copie o arquivo para `/usr/share/nginx/html/js/produtos-data.js` (container) ou `/var/www/html/js/` (host).
- **Recarregar do arquivo** ignora overrides salvos e mostra o conteúdo original do repositório.
- **Resetar** remove os overrides do `localStorage` e volta a usar os valores padrão do arquivo.

## 🧩 Personalização rápida (nome, logo, contatos)

### 1) Nome da loja
- Arquivos: `index.html`, `sobre.html`, `produtos.html`, `termos.html`, `suporte.html`
- Altere:
  - `<title>Sandlabs — ...</title>`
  - `<span class="brand-name">Sandlabs</span>`
- (Opcional) Pesquise por “Sandlabs” e substitua em todos os arquivos.

### 2) Logo
- Arquivo: `images/logo.png`
- Substitua o arquivo mantendo o **mesmo nome** e proporção aproximada.
- Se mudar o caminho ou nome, atualize os `<img src="...">` nos cabeçalhos.

### 3) Contatos (WhatsApp / Telegram)
- Arquivo: `js/compras.js`
- Altere as constantes no topo:
  ```js
  const WHATS = '41779786651'; // seu número com DDI/DDD
  const TELEGRAM = 'SeuUsuarioOuCanal'; // ex.: 'SandLabs_21'
  ```
- Esses contatos são usados pelos botões “WhatsApp/Telegram” dos modais.

### 4) Links de redes
- Arquivos: `sobre.html` e `suporte.html` (cards com botões).
- Atualize os `href` dos botões (Twitter/X, YouTube, Telegram, etc.).

---

## 🎨 Aparência (CSS / tokens / herói)

### Tokens principais
Arquivo: `css/style.css` (topo do arquivo)
```css
:root{
  --bg:#0a0a0a;           /* fundo geral */
  --text:#e6e6e6;         /* cor base do texto */
  --accent:#ff3838;       /* cor primária (botões) */
  --accent-2:#ff7b39;     /* gradiente secundário */
  --maxw:1180px;          /* largura máxima do conteúdo */
  /* ...outros tokens (radius, sombras, espaçamentos) */
}
```
> Ajuste essas variáveis para trocar rapidamente o tema, raio de borda, sombras, etc.

### Imagem de fundo do herói (home)
- O herói usa um **plano de fundo orgânico** configurado por CSS.
- Arquivo: `css/style.css` — classe `.hero-with-bg`
  ```css
  .hero-with-bg{ --hero-bg: url('../images/produto.png'); }
  .hero-with-bg::after{ background-image: var(--hero-bg); }
  ```
- **Opção 1 (global pelo CSS):** substitua `../images/produto.png` pelo seu arquivo.
- **Opção 2 (por página):** no `index.html`, defina inline:
  ```html
  <section class="hero hero-with-bg" style="--hero-bg:url('images/minha-img.png')">
  ```
> Caminho relativo: lembre que o CSS vive em `/css`, por isso `../images/...`.

---

## 🛒 Catálogo de produtos (a única fonte de verdade)

**Arquivo:** `js/produtos-data.js`  
Cada objeto representa um produto. Campos suportados:

```js
{
  id: 'slug-unico',               // obrigatório, usado para modais e finalização
  nome: 'Nome do Produto',
  imagens: ['images/prod1.png', 'images/prod1b.png', ...], // 1ª imagem vira capa
  resumo: 'Descrição curta do produto para cards.',
  preco: [
    { label: 'Variante/Item', valor: 'R$ 123' },
    { label: 'Box de Proteção', valor: 'R$ 89' }
  ],
  detalhesHTML: `
    <!-- HTML livre: links, listas, tutoriais, docs, etc. -->
    <p><strong>Especificações:</strong> ...</p>
    <p>Tutorial: <a href="https://..." target="_blank">YouTube</a></p>
  `,
  options: [
    // Conjuntos de opções que o modal vai renderizar automaticamente:
    { type:'colorPair', title:'Nome do Grupo', inputs:[
      { name:'campoA', label:'Case' },
      { name:'campoB', label:'Botões' }
    ]},
    { type:'colorSingle', title:'Uma cor só', input:{ name:'campoUnico', label:'Cor' } },
    { type:'seedPack' } // radio kit/single + quantidade (caso SandSeed)
  ],
  allowAddOnSeed: true,           // se true, mostra checkbox “Adicionar Kit SandSeed”
  buyButtonText: 'Comprar X',     // texto do botão de compra
  badge: { text:'Promo', variant:'promo' } // selo opcional (promo|new|neutral)
}
```

### ➕ Como adicionar um novo produto
1. **Crie o objeto** e **adicione ao array** `window.PRODUTOS` em `js/produtos-data.js`.
2. **Defina** um `id` único (ex.: `pico`, `kruxcase`, `meu-prod`).
3. **Inclua imagens** em `/images` e referencie em `imagens: [...]`.
4. (Opcional) Preencha `detalhesHTML` com links (docs, GitHub, YouTube, AliExpress).
5. **Escolha as `options`** conforme o produto:
   - `colorPair` → 2 cores (ex.: case + botões / box + alças).
   - `colorSingle` → 1 cor.
   - `seedPack` → controle de kit/avulsa (já trata quantidades).
6. Se vender add-on SandSeed para esse produto, marque `allowAddOnSeed: true`.
7. (Opcional) Adicione `badge` para selo no card (ex.: `{text:'Novo', variant:'new'}`).
8. Salve. **Pronto**:
   - A **home** exibirá o novo card.
   - A **página de produtos** criará galeria, descrição e **modal de compra**.
   - A **finalização** (Whats/Telegram) usará os dados e opções automaticamente.

> ⚠️ As **regras de validação** (ex.: exigir as duas cores em `colorPair`) já estão embutidas em `compras.js`. Você só precisa nomear corretamente os campos em `options`.

---

## 💬 Cupom (propagar entre páginas e inputs)

**Arquivo:** `js/cupom.js`  
O script:
- Lê `?cupom=XYZ` da URL.
- Salva em `localStorage`.
- Preenche **todos os inputs** de cupom nos modais.
- Anexa o `?cupom=...` a links internos, para o cupom “viajar” pelo site.

> Se não quiser essa função, remova a inclusão do `js/cupom.js` das páginas.

---

## 🪟 Modais de compra & rolagem

- Modais criados por `render-produtos.js` chamam `compras.js` na finalização.
- **Rolagem do fundo** é **bloqueada** quando o modal abre:
  - A classe `modal-open` é aplicada ao `<html>`/`<body>` (css já incluso).
- Fechamento ao clicar fora da caixa ou tecla **ESC**.

---

## 🧠 Lógica de compra (WhatsApp / Telegram)

**Arquivo:** `js/compras.js`  
- **Automático**: gera a mensagem a partir do **produto + opções selecionadas**.
- Basta manter `window.PRODUTOS` atualizado.
- Para trocar destinos:
  ```js
  const WHATS = '5544...';      // número com DDI/DDD
  const TELEGRAM = 'SeuUsuario'; // ex.: SandLabs_21
  ```

Mensagens geradas (exemplo):
```
vim pelo site sandlabs.store e gostaria de pedir
- Jade DIY
- Jade DIY: Case (Preto) + Botões (Vermelho)
- Box de Proteção: Box (Translúcido) + Alças (Preto)

pode calcular o frete para o cep: 12345-678
vim pelo (MEUCUPOM10)
```

---

## 🏷️ Selos (badges) nos cards

- Defina `badge` no produto:
  ```js
  badge: { text:'Promo', variant:'promo' } // variants: promo | new | neutral
  ```
- Estilo: `css/style.css` (classes `.card-badge`, `.promo`, `.new`, `.neutral`).

---

## 🖼️ Galeria e lightbox

- A galeria é montada com `imagens: []`.
- O lightbox é controlado por `render-produtos.js` (navegação anterior/próxima).
- As miniaturas usam `object-fit: cover` e `aspect-ratio` para manter grade bonita.

---

## 🧾 Termos, Sobre e Suporte

- **Termos:** edite `termos.html` (pagamentos, privacidade, prazos).
- **Sobre:** edite `sobre.html` (manifesto, canais).
- **Suporte:** edite links e textos em `suporte.html`.

---

## 🔍 SEO & Meta

- Atualize `<title>` e adicione meta tags nas páginas:
  ```html
  <meta name="description" content="Loja open-source de hardware Bitcoin — carteiras, cases e tutoriais."/>
  <meta property="og:title" content="Sua Loja — Início"/>
  <meta property="og:description" content="Hardware open-source para autocustódia."/>
  <meta property="og:image" content="images/produto.png"/>
  <meta name="theme-color" content="#000000"/>
  ```
- Adicione `favicon.ico`/`apple-touch-icon` em `/images` e os respectivos `<link>`.

---

## 🧹 Boas práticas para imagens

- Otimize (PNG/JPG/WebP) e mantenha nomes claros: `jade1.png`, `krux2.png`, etc.
- **Primeira imagem** do array é a capa do card.
- Use dimensões consistentes (ex.: 1200×900) para melhor corte/grade.

---

## 🔒 Privacidade

- Em `termos.html`, descreva como você trata CEP/endereços e quando apaga os dados.
- **Nunca** colecione dados além do necessário para envio/pedido.

---

## 🛠️ Licença & crédito

- Este projeto está sob **GPLv3**.
- Se adaptar, **remova** itens pessoais (logo/nomes/contatos) que indiquem relação com a Sandlabs original.
- Sinta-se livre para contribuir com PRs/melhorias.

---

## ❓FAQ rápido

- **“Onde adiciono um produto?”**  
  Em `js/produtos-data.js`. Só isso. O resto se ajusta.

- **“Como mudo WhatsApp/Telegram?”**  
  Em `js/compras.js`, altere `WHATS` e `TELEGRAM`.

- **“Quero trocar a imagem do herói.”**  
  Troque `images/produto.png` ou defina `--hero-bg:url('images/minha.png')` na seção do hero da home.

- **“Quero um selo de promoção.”**  
  Adicione `badge` no produto: `{ text:'Promo', variant:'promo' }`.

- **“Quero cupom em todas as páginas.”**  
  Mantenha `js/cupom.js` incluído e use URLs com `?cupom=SEUCU POM`.

---

**Bem-vindo ao mercado aberto do Bitcoin.**  
Construa, venda, documente e respeite seus clientes. 💛
