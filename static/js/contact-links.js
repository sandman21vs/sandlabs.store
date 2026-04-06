// /js/contact-links.js
// Atualiza links de contato conforme overrides carregados (ConfigStore/CONFIG)
(function(){
  function applyLinks(){
    const contacts = window.CONTACTS
      || (window.CONFIG && window.CONFIG.contacts)
      || { whatsapp:'41779786651', telegram:'SandLabs_21' };

    const whats = contacts.whatsapp || (window.CONFIG && window.CONFIG.whatsappNumber);
    const tele  = contacts.telegram  || (window.CONFIG && window.CONFIG.telegramUsername);

    const whatsLink = document.querySelector('[data-contact="whats"]');
    const teleLink  = document.querySelector('[data-contact="tele"]');

    if (whats && whatsLink) whatsLink.href = `https://wa.me/${whats}`;
    if (tele  && teleLink)  teleLink.href  = `https://t.me/${tele}`;
  }

  document.addEventListener('DOMContentLoaded', applyLinks);
})();
