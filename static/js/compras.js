// /js/compras.js  (SUBSTITUIR TODO O ARQUIVO)
// Finalização de compra automática baseada apenas no /js/produtos-data.js

(function(){
  const contacts = window.CONTACTS
    || (window.CONFIG && (CONFIG.contacts || {
      whatsapp: CONFIG.whatsappNumber,
      telegram: CONFIG.telegramUsername
    }))
    || { whatsapp:'41779786651', telegram:'SandLabs_21' };

  const WHATS = contacts.whatsapp || '41779786651';
  const TELEGRAM = contacts.telegram || 'SandLabs_21';

  function findProductById(id){
    const list = (window.PRODUTOS || []);
    return list.find(p => p.id === id) || null;
  }

  function formDataToObject(form){
    const data = {};
    const fd = new FormData(form);
    for (const [k, v] of fd.entries()){
      // se for checkbox sem valor custom, trate como "on"
      if (data[k] !== undefined){
        // múltiplos valores com mesmo name (se houver)
        if (!Array.isArray(data[k])) data[k] = [data[k]];
        data[k].push(v);
      } else {
        data[k] = v;
      }
    }
    // checkboxes desmarcados não vêm no FormData; garantimos flags
    form.querySelectorAll('input[type="checkbox"]').forEach(ch=>{
      if (!(ch.name in data)) data[ch.name] = false;
      else if (data[ch.name] === 'on') data[ch.name] = true;
    });
    return data;
  }

  function pickField(obj, hint){
    // retorna o primeiro valor cujo nome contenha "hint" (case-insensitive)
    const k = Object.keys(obj).find(key => key.toLowerCase().includes(hint));
    return k ? obj[k] : '';
  }

  function sanitize(val){ return (val || '').toString().trim(); }

  function buildOptionLines(prod, d){
    const lines = [];
    let error = '';

    (prod.options || []).forEach(opt=>{
      if (opt.type === 'colorPair'){
        const a = opt.inputs?.[0];
        const b = opt.inputs?.[1];
        const va = sanitize(d[a?.name]);
        const vb = sanitize(d[b?.name]);
        if ((va && !vb) || (!va && vb)){
          error = (window.t
            ? window.t('public.products.errors.select_both_colors', `Selecione ambas as cores para “{title}” ou deixe ambas em branco.`).replace('{title}', opt.title || '')
            : `Selecione ambas as cores para “${opt.title}” ou deixe ambas em branco.`);
          return;
        }
        if (va && vb){
          lines.push(`- ${opt.title}: ${a?.label||'A'} (${va}) + ${b?.label||'B'} (${vb})`);
        }
      }

      if (opt.type === 'colorSingle'){
        const i = opt.input;
        const v = sanitize(d[i?.name]);
        if (v){
          lines.push(`- ${opt.title}: ${i?.label||opt.title} (${v})`);
        }
      }

      if (opt.type === 'seedPack'){
        const pack = sanitize(d.seedPack);
        if (pack === 'kit'){
          lines.push(window.t ? window.t('commerce.js.message.sandseed_kit', '- SandSeed: kit 5 un (3 lisas + 2 perfuradas)') : '- SandSeed: kit 5 un (3 lisas + 2 perfuradas)');
        } else if (pack === 'single'){
          const q = Math.max(1, parseInt(d.seedQty || '1', 10) || 1);
          lines.push((window.t ? window.t('commerce.js.message.sandseed_single', '- SandSeed: {qty} placa(s) avulsa(s)') : `- SandSeed: ${q} placa(s) avulsas`).replace('{qty}', q));
        }
      }
    });

    return { lines, error };
  }

  function buildMessage(prod, d){
    const { lines, error } = buildOptionLines(prod, d);
    if (error) return { error, msg:'' };

    let msg = (window.t ? window.t('commerce.js.message.intro') : 'vim pelo site sandlabs.store e gostaria de pedir') + '\n';
    msg += `-${prod.nome}\n`;
    if (lines.length){
      msg += lines.join('\n') + '\n';
    }

    // add-on SandSeed (se disponível no produto)
    const addSeed = !!d.addSeedKit;
    if (addSeed && prod.allowAddOnSeed){
      msg += (window.t ? window.t('commerce.js.message.addon_seed', '- Adicionar: Kit SandSeed (5 placas)') : '- Adicionar: Kit SandSeed (5 placas)') + '\n';
    }

    // CEP e cupom
    const cep   = sanitize(pickField(d,'cep'));
    const cupom = sanitize(pickField(d,'cupom'));
    if (cep)   msg += `\n${(window.t ? window.t('commerce.js.message.shipping_postal_code') : 'pode calcular o frete para o cep:')} ${cep}`;
    if (cupom) msg += `\n${(window.t ? window.t('commerce.js.message.coupon_prefix') : 'vim pelo')} (${cupom})`;

    return { error:'', msg };
  }

  // API principal
  window.finalizeCompra = function(form, produtoId, plataforma){
    const prod = findProductById(produtoId);
    if (!prod){
      alert(window.t ? window.t('commerce.js.errors.product_not_found') : 'Produto não encontrado.');
      return;
    }

    const d = formDataToObject(form);
    const { error, msg } = buildMessage(prod, d);
    if (error){
      alert(error);
      return;
    }

    const url = (plataforma === 'whats')
      ? `https://wa.me/${WHATS}?text=${encodeURIComponent(msg)}`
      : `https://t.me/${TELEGRAM}?text=${encodeURIComponent(msg)}`;

    window.open(url, '_blank');
  };

  // Wrappers de compatibilidade com HTML antigo (mantêm funcionamento legado)
  window.confirmPurchaseWhats           = ()=> finalizeCompra(document.getElementById('buyForm'),       'jade','whats');
  window.confirmPurchaseTele            = ()=> finalizeCompra(document.getElementById('buyForm'),       'jade','tele');
  window.confirmPurchaseWhatsKruxModal  = ()=> finalizeCompra(document.getElementById('buyFormKrux'),   'krux','whats');
  window.confirmPurchaseTeleKruxModal   = ()=> finalizeCompra(document.getElementById('buyFormKrux'),   'krux','tele');
  window.confirmPurchaseWhatsNerdModal  = ()=> finalizeCompra(document.getElementById('buyFormNerd'),   'nerd','whats');
  window.confirmPurchaseTeleNerdModal   = ()=> finalizeCompra(document.getElementById('buyFormNerd'),   'nerd','tele');
  window.confirmPurchaseWhatsSeed       = ()=> finalizeCompra(document.getElementById('buyFormSeed'),   'sandseed','whats');
  window.confirmPurchaseTeleSeed        = ()=> finalizeCompra(document.getElementById('buyFormSeed'),   'sandseed','tele');
  window.confirmPurchaseWhatsPico       = ()=> finalizeCompra(document.getElementById('buyFormPico'),   'pico','whats');
  window.confirmPurchaseTelePico        = ()=> finalizeCompra(document.getElementById('buyFormPico'),   'pico','tele');
  window.confirmPurchaseWhatsKruxCaseModal = ()=> finalizeCompra(document.getElementById('buyFormKruxCase'), 'kruxcase','whats');
  window.confirmPurchaseTeleKruxCaseModal  = ()=> finalizeCompra(document.getElementById('buyFormKruxCase'), 'kruxcase','tele');
})();
