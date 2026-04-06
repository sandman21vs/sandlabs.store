// /js/lightbox.js — ARQUIVO COMPLETO
(function(){
  let imagens = [];
  let indice = 0;
  let mounted = false;

  function montaLightbox(){
    if (mounted) return;
    let lb = document.getElementById('lightbox');
    if (!lb) {
      lb = document.createElement('div');
      lb.id = 'lightbox';
      lb.className = 'lightbox';
      document.body.appendChild(lb);
    }
    lb.innerHTML = `
      <div class="lightbox-inner" role="dialog" aria-modal="true">
        <button class="close-btn" data-action="close" aria-label="Fechar">×</button>
        <figure class="lightbox-figure">
          <img id="imagemModal" alt="Imagem ampliada" decoding="async" loading="eager"/>
        </figure>
        <button class="nav-btn prev-btn" data-action="prev" aria-label="Anterior">&#10094;</button>
        <button class="nav-btn next-btn" data-action="next" aria-label="Próxima">&#10095;</button>
      </div>
    `;

    lb.addEventListener('click', function(e){
      const btn = e.target.closest('[data-action]');
      if (btn) {
        const a = btn.getAttribute('data-action');
        if (a === 'close') fechar();
        if (a === 'prev') anterior();
        if (a === 'next') proxima();
        return;
      }
      // clique fora da imagem fecha
      const inner = e.target.closest('.lightbox-inner');
      if (!inner) fechar();
    });

    window.addEventListener('keydown', function(e){
      if (lb.style.display !== 'flex') return;
      if (e.key === 'Escape') fechar();
      else if (e.key === 'ArrowLeft') anterior();
      else if (e.key === 'ArrowRight') proxima();
    });

    mounted = true;
  }

  function abrir(imgs, startIndex){
    montaLightbox();
    const lb = document.getElementById('lightbox');
    imagens = Array.isArray(imgs) ? imgs.slice() : [];
    indice = Number.isInteger(startIndex) ? startIndex : 0;
    if (!imagens.length) return;

    const img = document.getElementById('imagemModal');
    img.src = imagens[indice];

    lb.style.display = 'flex';
    document.documentElement.classList.add('modal-open');
    document.body.classList.add('modal-open');
  }

  function fechar(){
    const lb = document.getElementById('lightbox');
    if (!lb) return;
    lb.style.display = 'none';
    document.documentElement.classList.remove('modal-open');
    document.body.classList.remove('modal-open');
  }

  function anterior(){
    if (!imagens.length) return;
    indice = (indice - 1 + imagens.length) % imagens.length;
    document.getElementById('imagemModal').src = imagens[indice];
  }

  function proxima(){
    if (!imagens.length) return;
    indice = (indice + 1) % imagens.length;
    document.getElementById('imagemModal').src = imagens[indice];
  }

  // Exporta API global usada por render-produtos.js
  window.lightbox = { open: abrir, close: fechar, prev: anterior, next: proxima, mount: montaLightbox };

  // Monta ao carregar a página
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', montaLightbox);
  } else {
    montaLightbox();
  }
})();
