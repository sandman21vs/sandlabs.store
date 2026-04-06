// /js/render-home.js (NOVO ARQUIVO)
(function(){
  function el(tag, attrs={}, html){
    const e = document.createElement(tag);
    Object.entries(attrs).forEach(([k,v])=>{
      if (k==='class') e.className = v;
      else e.setAttribute(k,v);
    });
    if (html!=null) e.innerHTML = html;
    return e;
  }

  function buildCard(prod){
    const a = el('article','',null);
    a.className = 'card product soft-shadow hover-lift';
    a.addEventListener('click',()=>location.href='produtos.html');

    // badge (selo de promoção/novo/etc)
    if (prod.badge && prod.badge.text){
      const b = el('span', { class:`card-badge ${prod.badge.variant||''}` }, prod.badge.text);
      a.appendChild(b);
    }

    const media = el('div',{class:'card-media'});
    media.appendChild(el('img',{
      src: (prod.imagens && prod.imagens[0]) || '',
      alt: prod.nome,
      loading:'lazy',
      decoding:'async'
    }));
    a.appendChild(media);

    const body = el('div',{class:'card-body'});
    body.appendChild(el('h3',{class:'card-title'}, prod.nome));
    body.appendChild(el('p',{class:'card-text'}, prod.resumo));

    const price = el('div',{class:'price-line'});
    const p0 = Array.isArray(prod.preco) && prod.preco[0] ? prod.preco[0].valor : '';
    const p1 = Array.isArray(prod.preco) && prod.preco[1] ? `${prod.preco[1].label} ${prod.preco[1].valor}` : '';
    price.innerHTML = `<span>${p0}</span><span class="muted">${p1}</span>`;
    body.appendChild(price);

    a.appendChild(body);
    return a;
  }

  window.addEventListener('DOMContentLoaded', ()=>{
    const wrap = document.getElementById('home-products');
    if (!wrap) return;
    wrap.innerHTML='';
    (window.PRODUTOS||[]).forEach(prod=> wrap.appendChild(buildCard(prod)));
  });
})();
