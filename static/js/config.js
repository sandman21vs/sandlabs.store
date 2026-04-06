// /js/config.js  (NOVO ARQUIVO)
const DEFAULT_WHATS = '41779786651';
const DEFAULT_TELE  = 'SandLabs_21';

window.CONFIG = {
  // Contatos padrão usados em compras e na página de suporte
  contacts: {
    whatsapp: DEFAULT_WHATS,
    telegram: DEFAULT_TELE
  },
  whatsappNumber: DEFAULT_WHATS,     // compatibilidade com código legado
  telegramUsername: DEFAULT_TELE,    // compatibilidade com código legado

  // Paleta de cores usada nos seletores de produto
  colors: [
    { id: 'amarelo',     nome: 'Amarelo' },
    { id: 'azul',        nome: 'Azul' },
    { id: 'laranja',     nome: 'Laranja' },
    { id: 'preto',       nome: 'Preto' },
    { id: 'translucido', nome: 'Translúcido' },
    { id: 'vermelho',    nome: 'Vermelho' }
  ]
};
