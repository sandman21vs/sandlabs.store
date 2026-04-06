// /js/color-selector.js  (NOVO ARQUIVO)
(function(){
  function buildColorSelector(container, inputName) {
    const colors = (window.CONFIG && CONFIG.colors) ? CONFIG.colors : [];
    colors.forEach(c => {
      const label = document.createElement('label');

      const input = document.createElement('input');
      input.type = 'radio';
      input.name = inputName;
      input.value = c.nome;

      const img = document.createElement('img');
      img.src = `images/cor_${c.id}.png`;
      img.alt = c.nome;

      label.appendChild(input);
      label.appendChild(img);
      container.appendChild(label);
    });
  }

  window.buildColorSelector = buildColorSelector;
})();
