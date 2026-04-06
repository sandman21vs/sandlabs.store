(function(){
    var container = document.getElementById('payment-container');
    if (!container) return;

    var checkUrl = container.dataset.checkUrl;
    var successUrl = container.dataset.successUrl;
    var status = document.getElementById('payment-status');
    var pollInterval = 2000;

    var timer = setInterval(function(){
        fetch(checkUrl)
        .then(function(r){ return r.json(); })
        .then(function(data){
            if (data.paid) {
                clearInterval(timer);
                status.textContent = 'Pagamento confirmado!';
                status.className = 'invoice-status invoice-paid';
                setTimeout(function(){
                    window.location.href = successUrl;
                }, 2000);
            }
        });
    }, pollInterval);

    var copyBtn = document.getElementById('copy-bolt11');
    if (copyBtn) {
        copyBtn.addEventListener('click', function(){
            var bolt11 = document.getElementById('bolt11-text').textContent;
            navigator.clipboard.writeText(bolt11);
            copyBtn.textContent = 'Copiado!';
            setTimeout(function(){ copyBtn.textContent = 'Copiar'; }, 2000);
        });
    }
})();
