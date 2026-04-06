// /js/produtos-data.js  (SUBSTITUIR TODO O ARQUIVO)
// Mantém TODAS as infos do antigo e adiciona suporte a `badge` (selo opcional)
window.PRODUTOS = [
  {
    id: 'jade',
    nome: 'Jade DIY',
    imagens: [
      'images/jade1.png','images/jade2.png','images/jade3.png',
      'images/jade4.png','images/jade5.png','images/jade6.png',
      'images/jade7.png','images/jade8.png','images/jade9.png'
    ],
    resumo: 'Carteira de hardware open-source, segura e flexível.',
    preco: [
      { label: 'Jade DIY', valor: 'R$ 230' },
      { label: 'Box de Proteção', valor: 'R$ 70' }
    ],
    detalhesHTML: `
      <h4>Documentação do Dispositivo JADE DIY</h4>
      <p><strong>Introdução:</strong> dispositivo seguro e transparente.</p>
      <p><strong>Por que hardware open source?</strong> <a href="https://plebs.substack.com/p/hard-wallets-seguras" target="_blank">Artigo</a></p>
      <p><strong>Conectividade:</strong> GreenWallet • SideSwap • Sparrow • Electrum</p>
      <p><strong>Atualizações:</strong> via navegador / binários Sandmann / compilação GitHub</p>
      <p><strong>Bateria:</strong> interna (indicação limitada)</p>
      <p><strong>Segurança:</strong> Secure-element virtual Oracle</p>
      <p>Tutorial: <a href="https://www.youtube.com/watch?v=k-maFZiKSw4" target="_blank">YouTube</a></p>
      <p><a href="https://docs.google.com/document/d/1Bf8O-R478woq8z7Z8DnN9XlfGf9B3GT8rn0qgJiAUHM/edit?usp=sharing" target="_blank">Documentação completa</a></p>
    `,
    options: [
      { type: 'colorPair', title: 'Jade DIY', inputs: [
        { name:'jadeColor',   label:'Case'   },
        { name:'buttonColor', label:'Botões' }
      ]},
      { type: 'colorPair', title: 'Box de Proteção', inputs: [
        { name:'boxColor',    label:'Box'   },
        { name:'handleColor', label:'Alças' }
      ]}
    ],
    allowAddOnSeed: true,
    buyButtonText: 'Comprar Jade DIY',
    badge: { text:'Promo', variant:'promo' }   // ← selo opcional
  },


  
  {
    id: 'pico',
    nome: 'PicoFido / PicoKey (RP2040 • FIDO2)',
    imagens: ['images/pico1.png','images/pico2.png','images/pico3.png'],
    resumo: 'Chave de segurança FIDO-U2F / FIDO2 baseada no RP2040 (USB-C).',
    preco: [{ label: 'PicoFido / PicoKey', valor: 'R$ 159' }],
    detalhesHTML: `
      <h4>Detalhes Técnicos</h4>
      <p>• Projeto 100% open-source — código, esquemas e guias em
         <a href="https://github.com/polhenarejos/pico-fido" target="_blank">github.com/polhenarejos/pico-fido</a>.</p>
      <p>• Compatível: Google, Proton Mail, Microsoft Outlook, GitHub, X/Twitter…</p>
      <p>• FIDO2 dispensa SMS/app 2FA; chaves ficam no dispositivo.</p>
      <p>• USB-C fêmea; alimentação do host (cabo não incluído).</p>
      <p>• Conectividade: Android • Linux • Windows (iOS/macOS não testados).</p>
      <p>• <a href="https://docs.google.com/document/d/1JIE_6lNlFsk-TwPceDngePEg8G9fe3FKINjHCGeSUgg/edit?usp=drive_link" target="_blank">Documentação completa</a>.</p>
    `,
    options: [
      { type:'colorPair', title:'Cores', inputs:[
        { name:'picoBodyColor', label:'Corpo' },
        { name:'picoRingColor', label:'Anel'  }
      ]}
    ],
    allowAddOnSeed: true,
    buyButtonText: 'Comprar PicoFido',
    badge: { text:'Novo', variant:'new' }
  },

  {
    id: 'nerd',
    nome: 'NerdMiner — CASE (sem bateria)',
    imagens: ['images/nm1.png','images/nm2.png','images/nm3.png'],
    resumo: 'CASE para NerdMiner (TTGO T-Display). *Não inclui bateria nem placa.',
    preco: [{ label: 'Case TTGO T-Display', valor:'R$ 70' }],
    detalhesHTML: `
      <p>• ~55 KH/s (info do projeto) • Stratum / pools self-custody.<br>
      • Firmware: <a href="https://github.com/BitMaker-hub/NerdMiner_v2" target="_blank">GitHub</a>.<br>
      • USB-C 5 V • Tutorial: <a href="https://www.youtube.com/watch?v=Cq0y1034oq8" target="_blank">YouTube</a>.</p>
      <p><strong>TTGO T-Display:</strong> <a href="https://pt.aliexpress.com/item/1005005970553639.html?channel=twinner" target="_blank">Comprar no AliExpress</a></p>
      <p><em>APENAS CASE — sem bateria.</em></p>
    `,
    options: [
      { type: 'colorPair', title: 'Cores do Case', inputs: [
        { name:'nerdCaseColor',   label:'Case'   },
        { name:'nerdButtonColor', label:'Botões' }
      ]}
    ],
    allowAddOnSeed: true,
    buyButtonText: 'Comprar NerdMiner',
    badge: { text:'Case', variant:'neutral' }
  },

  {
    id: 'sandseed',
    nome: 'SandSeed – placas para backup de seed',
    imagens: ['images/sandseed1.png','images/sandseed2.png'],
    resumo: 'Kit Stakbit 1248 – 5 placas (3 lisas + 2 perfuradas) padrão BIP-39.',
    preco: [
      { label: 'Placa avulsa', valor: '2 000 sats' },
      { label: 'Kit 5 un',     valor: '5 000 sats' }
    ],
    detalhesHTML: `
      <p><strong>Como usar:</strong> sobre base firme, perfure cada letra (estilete, agulha grossa ou punção).</p>
      <p><strong>Utilidade:</strong> gravação física, offline e resistente ao fogo/água das 24 palavras da seed BIP-39.</p>
      <p>Tutorial:
         <a href="https://stackbit.me/tutorial-stackbit-1248/" target="_blank">Vídeo oficial (Stackbit)</a></p>
      <p style="font-size:.9rem;color:#ccc">
        Design original por <a href="https://twitter.com/valandro" target="_blank">@Valandro</a>.
        Versão em aço inox na <a href="https://stackbit.me/tutorial-stackbit-1248/#loja" target="_blank">loja do autor</a>.
      </p>
    `,
    options: [{ type: 'seedPack' }],
    allowAddOnSeed: false,
    buyButtonText: 'Comprar SandSeed',
    badge: { text:'Sats', variant:'neutral' }
  },

  {
    id: 'krux',
    nome: 'Krux Yahboom Modcase (c/ bateria)',
    imagens: ['images/krux1.png','images/krux2.png','images/krux3.png','images/krux4.png'],
    resumo: 'Modcase com bateria; placa eletrônica não inclusa.',
    preco: [
      { label: 'Modcase',          valor: 'R$ 250' },
      { label: 'Box de Proteção',  valor: 'R$ 89'  }
    ],
    detalhesHTML: `
      <h4>Detalhes Técnicos</h4>
      <p>Inclui bateria e box de proteção (placa não inclusa).</p>
      <p>Tutorial: <a href="https://www.youtube.com/watch?v=V48RpmuZEwI" target="_blank">YouTube</a></p>
      <p>Placa referência Yahboom:
         <a href="https://de.aliexpress.com/item/1005005585064305.html" target="_blank">AliExpress</a></p>
      <p>Documentação:
         <a href="https://docs.google.com/document/d/1s70HUmdX3XX08GbINxEAay5eK_D3c4RLReKuautZYB4/edit?usp=sharing" target="_blank">Google Docs</a></p>
      <p>Encomenda completa: ~25 dias • R$ 775 + R$ 89 (box)</p>
    `,
    options: [
      { type:'colorSingle', title:'Modcase (opcional)', input:{ name:'kruxColor', label:'Modcase' } },
      { type:'colorPair',   title:'Box de Proteção (opcional)', inputs:[
        { name:'kruxBoxColor',    label:'Box'   },
        { name:'kruxHandleColor', label:'Alças' }
      ]}
    ],
    allowAddOnSeed: true,
    buyButtonText: 'Comprar Modcase',
    badge: null
  },

  {
    id: 'kruxcase',
    nome: 'Krux Yahboom Case (impressão 3D)',
    imagens: ['images/kruxcase1.png','images/kruxcase2.png','images/kruxcase3.png'],
    resumo: 'Somente impressão 3D do case. Compatível com placas Krux Yahboom.',
    preco: [{ label:'Case', valor:'R$ 90' }],
    detalhesHTML: `
      <p>Impressão 3D em PLA/ASA sob encomenda. Não inclui eletrônica.</p>
    `,
    options: [
      { type:'colorSingle', title:'Case', input:{ name:'kruxCaseColor', label:'Case' } },
      { type:'colorPair',   title:'Box de Proteção (opcional)', inputs:[
        { name:'kruxCaseBoxColor',    label:'Box'   },
        { name:'kruxCaseHandleColor', label:'Alças' }
      ]}
    ],
    allowAddOnSeed: true,
    buyButtonText: 'Comprar Case',
    badge: { text:'3D', variant:'neutral' }
  },



  {
    id: 'ttgo-case-bateria',
    nome: 'Case TTGO T-Display (com bateria)',
    imagens: ['images/jadecase2.png','images/jadecase3.png','images/jadecase7.png','images/jade9.png'],
    resumo: 'Case para TTGO T-Display com bateria integrada. *Não inclui a placa.',
    preco: [
      { label: 'Case c/ bateria', valor: 'R$ 120' },
      { label: 'Box de Proteção', valor: 'R$ 70' }
    ],
    detalhesHTML: `
      <p><strong>Compatibilidade:</strong> TTGO T-Display.</p>
      <p><strong>Observação:</strong> produto se refere apenas ao <em>case</em>; a placa TTGO não está inclusa.</p>
      <p><strong>TTGO T-Display (referência):</strong>
        <a href="https://pt.aliexpress.com/item/1005005970553639.html?channel=twinner" target="_blank">AliExpress</a>
      </p>
      <p><strong>Montagem (vídeo):</strong> <a href="https://youtu.be/S5LI_bG9f1U" target="_blank">YouTube</a></p>
    `,
    options: [
      { type: 'colorPair', title: 'Cores do Case', inputs: [
        { name:'ttgoCaseColor',   label:'Case'   },
        { name:'ttgoButtonColor', label:'Botões' }
      ]},
      { type: 'colorPair', title: 'Box de Proteção (opcional)', inputs: [
        { name:'ttgoBoxColor',    label:'Box'   },
        { name:'ttgoHandleColor', label:'Alças' }
      ]}
    ],
    allowAddOnSeed: true,
    buyButtonText: 'Comprar Case (c/ bateria)',
    badge: { text:'Novo', variant:'new' }
  },

  {
    id: 'jade-diy-sem-bateria',
    nome: 'Jade DIY (TTGO T-Display, sem bateria)',
    imagens: ['images/jade2.png','images/jade3.png','images/jade7.png','images/jade9.png'],
    resumo: 'Case para Jade DIY sem bateria integrada. *Não inclui a placa.',
    preco: [
      { label: 'Jade DIY (sem bateria)', valor: 'R$ 150' },
      { label: 'Box de Proteção', valor: 'R$ 70' }
    ],
    detalhesHTML: `
      <p><strong>Compatibilidade:</strong> TTGO T-Display (Jade DIY).</p>
      <p><strong>Observação:</strong> produto se refere apenas ao <em>case</em> sem bateria; a placa TTGO não está inclusa.</p>
      <p><strong>TTGO T-Display (referência):</strong>
        <a href="https://pt.aliexpress.com/item/1005005970553639.html?channel=twinner" target="_blank">AliExpress</a>
      </p>
      <p><strong>Documentação Jade DIY:</strong>
        <a href="https://docs.google.com/document/d/1Bf8O-R478woq8z7Z8DnN9XlfGf9B3GT8rn0qgJiAUHM/edit?usp=sharing" target="_blank">Google Docs</a>
      </p>
      <p><strong>Montagem (vídeo):</strong> <a href="https://youtu.be/S5LI_bG9f1U" target="_blank">YouTube</a></p>
    `,
    options: [
      { type: 'colorPair', title: 'Cores do Case', inputs: [
        { name:'jadeNoBatCaseColor',   label:'Case'   },
        { name:'jadeNoBatButtonColor', label:'Botões' }
      ]},
      { type: 'colorPair', title: 'Box de Proteção (opcional)', inputs: [
        { name:'jadeNoBatBoxColor',    label:'Box'   },
        { name:'jadeNoBatHandleColor', label:'Alças' }
      ]}
    ],
    allowAddOnSeed: true,
    buyButtonText: 'Comprar Jade DIY (sem bateria)',
    badge: { text:'Econômico', variant:'neutral' }
  },

{
  id: 'ttgo-case-sem-bateria',
  nome: 'TTGO T-Display — Case (sem bateria)',
  imagens: ['images/jade2.png','images/jade3.png','images/jade7.png','images/jade9.png'],
  resumo: 'Case para TTGO T-Display SEM bateria integrada. *Não inclui a placa.',
  preco: [
    { label: 'Case sem bateria', valor: 'R$ 70' },
    { label: 'Box de Proteção', valor: 'R$ 70' }
  ],
  detalhesHTML: `
    <p><strong>Compatibilidade:</strong> TTGO T-Display.</p>
    <p><strong>Observação:</strong> produto refere-se apenas ao <em>case</em> sem bateria; a placa TTGO não está inclusa.</p>
    <p><strong>TTGO T-Display (referência de compra):</strong>
      <a href="https://pt.aliexpress.com/item/1005005970553639.html?channel=twinner" target="_blank">AliExpress</a>
    </p>
    <p><strong>Montagem (vídeo):</strong> <a href="https://youtu.be/S5LI_bG9f1U" target="_blank">YouTube</a></p>
  `,
  options: [
    { type: 'colorPair', title: 'Cores do Case', inputs: [
      { name:'ttgoNoBatCaseColor',   label:'Case'   },
      { name:'ttgoNoBatButtonColor', label:'Botões' }
    ]},
    { type: 'colorPair', title: 'Box de Proteção (opcional)', inputs: [
      { name:'ttgoNoBatBoxColor',    label:'Box'   },
      { name:'ttgoNoBatHandleColor', label:'Alças' }
    ]}
  ],
  allowAddOnSeed: true,
  buyButtonText: 'Comprar Case (sem bateria)',
  badge: { text:'Sem bateria', variant:'neutral' }
},




];

