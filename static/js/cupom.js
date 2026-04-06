// /js/cupom.js  (NOVO ARQUIVO)  — leitura e aplicação do cupom em todas as páginas
(function () {
  function applyCupomToInputs(c) {
    if (!c) return;
    document.querySelectorAll("input[name='cupom']").forEach(input => { input.value = c; });
  }

  function addCupomToInternalLinks(c) {
    if (!c) return;
    document.querySelectorAll("a").forEach(link => {
      let href = link.getAttribute("href");
      if (!href) return;
      if (href.startsWith("http")) return;
      if (href.includes("cupom=")) return;
      const sep = href.includes("?") ? "&" : "?";
      link.setAttribute("href", `${href}${sep}cupom=${encodeURIComponent(c)}`);
    });
  }

  window.addEventListener("DOMContentLoaded", function () {
    const params = new URLSearchParams(location.search);
    let cupom = params.get("cupom");
    if (cupom) {
      localStorage.setItem("cupom", cupom);
    } else {
      cupom = localStorage.getItem("cupom");
    }
    applyCupomToInputs(cupom);
    addCupomToInternalLinks(cupom);
  });
})();
