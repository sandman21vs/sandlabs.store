// ---------- produtos.js (otimizado + NerdMiner + SandSeed + add‑on) ----------

/* 1. Galerias e Lightbox
   ------------------------------------------------------------------ */
   const galerias = {
    jade: [
      'images/jade1.png','images/jade2.png','images/jade3.png',
      'images/jade4.png','images/jade5.png','images/jade6.png',
      'images/jade7.png','images/jade8.png','images/jade9.png'
    ],
    krux: [
      'images/krux1.png','images/krux2.png','images/krux3.png','images/krux4.png'
    ],
    nerd: [
      'images/nm1.png','images/nm2.png','images/nm3.png'
    ],
    sandseed: [
      'images/sandseed1.png','images/sandseed2.png'
    ]
  };
  
  let galeriaAtual=[], indiceAtual=0;
  function abrirImagem(tipo,i){galeriaAtual=galerias[tipo]||[];indiceAtual=i;if(!galeriaAtual.length)return;
    document.getElementById('imagemModal').src=galeriaAtual[i];
    document.getElementById('lightbox').style.display='flex';
  }
  const fecharLightbox=()=>document.getElementById('lightbox').style.display='none';
  function imagemAnterior(){if(!galeriaAtual.length)return;
    indiceAtual=(indiceAtual-1+galeriaAtual.length)%galeriaAtual.length;
    document.getElementById('imagemModal').src=galeriaAtual[indiceAtual];
  }
  function proximaImagem(){if(!galeriaAtual.length)return;
    indiceAtual=(indiceAtual+1)%galeriaAtual.length;
    document.getElementById('imagemModal').src=galeriaAtual[indiceAtual];
  }
  
  /* 2. Seletor de cores genérico
     ------------------------------------------------------------------ */
  const COLORS=[
    {id:'amarelo',nome:'Amarelo'},{id:'azul',nome:'Azul'},{id:'laranja',nome:'Laranja'},
    {id:'preto',nome:'Preto'},{id:'translucido',nome:'Translúcido'},{id:'vermelho',nome:'Vermelho'}
  ];
  function buildColorSelector(container,inputName){
    COLORS.forEach(c=>{
      const l=document.createElement('label');
      l.append(Object.assign(document.createElement('input'),{type:'radio',name:inputName,value:c.nome}),
               Object.assign(document.createElement('img'),{src:`images/cor_${c.id}.png`,alt:c.nome}));
      container.appendChild(l);
    });
  }
  document.addEventListener('DOMContentLoaded',()=>
    document.querySelectorAll('[data-color-input]').forEach(el=>buildColorSelector(el,el.dataset.colorInput))
  );
  
  /* 3. Finalização de compra
     ------------------------------------------------------------------ */
  function finalizeCompra(form,produto,plataforma){
    const d=Object.fromEntries(new FormData(form).entries());
    const cep=d.cep||d.kruxCep||d.nerdCep||d.seedCep||'';
    const cupom=(d.cupom||d.kruxCupom||d.nerdCupom||d.seedCupom||'').trim();
    const addSeedKit=!!d.addSeedKit;            /* ← checkbox de add‑on  */
    let msg='';
  
    /* ---- Jade ---- */
    if(produto==='jade'){
      const jade=d.jadeColor&&d.buttonColor;
      const box =d.boxColor &&d.handleColor;
      if((d.jadeColor&&!d.buttonColor)||(!d.jadeColor&&d.buttonColor))
        return alert('Selecione ambas as cores para a Jade DIY (Case e Botões) ou deixe ambas em branco.');
      if((d.boxColor&&!d.handleColor)||(!d.boxColor&&d.handleColor))
        return alert('Selecione ambas as cores para a Box de Proteção (Box e Alças) ou deixe ambas em branco.');
      if(!jade&&!box) return alert('Selecione ao menos Jade DIY ou Box de Proteção.');
  
      msg+='vim pelo site sandlabs.store e gostaria de pedir uma\n';
      if(jade) msg+=`-jade (${d.jadeColor}) com botões (${d.buttonColor})\n`;
      if(jade&&box) msg+='e uma \n';
      if(box)  msg+=`-box de proteção (${d.boxColor}) com alças (${d.handleColor}) ,\n`;
    }
  
    /* ---- Krux ---- */
    else if(produto==='krux'){
      const mod=d.kruxColor;
      const box=d.kruxBoxColor&&d.kruxHandleColor;
      if(!mod&&!box) return alert('Selecione a cor do Modcase ou as cores do Box de Proteção.');
      if((d.kruxBoxColor&&!d.kruxHandleColor)||(!d.kruxBoxColor&&d.kruxHandleColor))
        return alert('Selecione ambas as cores para o Box de Proteção (Box e Alças) ou deixe ambas em branco.');
  
      msg+='vim pelo site sandlabs.store e gostaria de pedir uma\n';
      if(mod) msg+=`-krux yahboom modcase: Modcase (${d.kruxColor})\n`;
      if(mod&&box) msg+='e uma \n';
      if(box) msg+=`-box de proteção: Box (${d.kruxBoxColor}) com Alças (${d.kruxHandleColor}) ,\n`;
    }
  
    /* ---- NerdMiner ---- */
    else if(produto==='nerd'){
      const caseCol=d.nerdCaseColor, btnCol=d.nerdButtonColor;
      if((caseCol&&!btnCol)||(!caseCol&&btnCol))
        return alert('Selecione ambas as cores do NerdMiner (Case e Botões) ou deixe ambas em branco.');
      if(!caseCol&&!btnCol)
        return alert('Selecione a cor do Case e dos Botões do NerdMiner.');
  
      msg+='vim pelo site sandlabs.store e gostaria de pedir um\n';
      msg+=`-NerdMiner: Case (${caseCol}) com Botões (${btnCol})\n`;
    }
  
    /* ---- SandSeed standalone ---- */
    else if(produto==='sandseed'){
      const pack=d.seedPack;
      msg+='vim pelo site sandlabs.store e gostaria de pedir\n';
      if(pack==='kit') msg+='-SandSeed: kit 5 un (3 lisas + 2 perfuradas) – 5 000 sats\n';
      else{
        const q=Number(d.seedQty)||1;
        msg+=`-SandSeed: ${q} placa(s) avulsas – ${q*2000} sats\n`;
      }
    }
  
    /* ---- add‑on SandSeed kit ---- */
    if(addSeedKit && produto!=='sandseed'){
      msg += '-SandSeed: kit 5 un (3 lisas + 2 perfuradas) – 5 000 sats\n';
    }
  
    /* ---- Fecho comum ---- */
    msg+=`\npode calcular o frete para o cep: ${cep}`;
    if(cupom) msg+=`\nvim pelo (${cupom})`;
  
    const url=(plataforma==='whats')
      ? `https://wa.me/41779786651?text=${encodeURIComponent(msg)}`
      : `https://t.me/SandLabs_21?text=${encodeURIComponent(msg)}`;
    window.open(url,'_blank');
  }
  
  /* 4. Wrappers  ------------------------------------------------------------ */
  function confirmPurchaseWhats()          {finalizeCompra(buyForm,'jade','whats');}
  function confirmPurchaseTele()           {finalizeCompra(buyForm,'jade','tele'); }
  function confirmPurchaseWhatsKruxModal() {finalizeCompra(buyFormKrux,'krux','whats');}
  function confirmPurchaseTeleKruxModal()  {finalizeCompra(buyFormKrux,'krux','tele');}
  function confirmPurchaseWhatsNerdModal() {finalizeCompra(buyFormNerd,'nerd','whats');}
  function confirmPurchaseTeleNerdModal()  {finalizeCompra(buyFormNerd,'nerd','tele');}
  function confirmPurchaseWhatsSeed()      {finalizeCompra(buyFormSeed,'sandseed','whats');}
  function confirmPurchaseTeleSeed()       {finalizeCompra(buyFormSeed,'sandseed','tele');}
  
  /* 5. Controles de modais -------------------------------------------------- */
  const showModal=id=>document.getElementById(id).style.display='block';
  const hideModal=id=>document.getElementById(id).style.display='none';
  
  function openBuyModal(){showModal('buyModal')}          function closeBuyModal(){hideModal('buyModal')}
  function openBuyModalKrux(){showModal('buyModalKrux')}  function closeBuyModalKrux(){hideModal('buyModalKrux')}
  function openBuyModalNerd(){showModal('buyModalNerd')}  function closeBuyModalNerd(){hideModal('buyModalNerd')}
  function openBuyModalSeed(){showModal('buyModalSeed')}  function closeBuyModalSeed(){hideModal('buyModalSeed')}
  function toggleInfoNerd(){typeof toggle==='function'&&toggle('infoDetalhadaNerd')}
  function toggleInfoSeed(){ toggle('infoDetalhadaSeed'); }

  