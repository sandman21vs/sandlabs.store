// Substitua o número pelo seu WhatsApp real
document.getElementById('buyBtn').addEventListener('click', () => {
    const whatsappNumber = '44997272087'; // Exemplo
    const whatsappUrl = `https://wa.me/${whatsappNumber}?text=Ola%20%2C%20vim%20pelo%20@sandlabs.store`;
    window.open(whatsappUrl, '_blank');
  });
  
<script>
  window.addEventListener("DOMContentLoaded", function() {
    // Verifica se a URL possui o parâmetro "cupom"
    const urlParams = new URLSearchParams(window.location.search);
    let cupom = urlParams.get("cupom");
    if (cupom) {
      // Armazena no localStorage para persistir entre as páginas
      localStorage.setItem("cupom", cupom);
    } else {
      // Recupera do localStorage se o parâmetro não estiver na URL
      cupom = localStorage.getItem("cupom");
    }
    if (cupom) {
      // Preenche todos os inputs com name "cupom" e "kruxCupom"
      document.querySelectorAll("input[name='cupom'], input[name='kruxCupom']").forEach(input => {
        input.value = cupom;
      });
      // Atualiza links internos para incluir o cupom na URL
      document.querySelectorAll("a").forEach(link => {
        let href = link.getAttribute("href");
        // Se o link for relativo e não conter "cupom="
        if (href && !href.startsWith("http") && href.indexOf("cupom=") === -1) {
          // Adiciona o parâmetro, usando & se já houver outros parâmetros
          if (href.indexOf("?") !== -1) {
            href += `&cupom=${encodeURIComponent(cupom)}`;
          } else {
            href += `?cupom=${encodeURIComponent(cupom)}`;
          }
          link.setAttribute("href", href);
        }
      });
    }
  });
</script>
