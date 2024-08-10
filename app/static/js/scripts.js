$(document).ready(function () {
    // Navbar animation
    setTimeout(function () { test(); });

    $(window).on('resize', function () {
        setTimeout(function () { test(); }, 500);
    });

    $(".navbar-toggler").click(function () {
        $(".navbar-collapse").slideToggle(300);
        setTimeout(function () { test(); });
    });

    // Configuração do MaskMoney
    $('#amount').maskMoney({
        prefix: 'R$ ',
        allowNegative: false,
        thousands: '.',
        decimal: ',',
        affixesStay: true,
        precision: 2
    });

    // Formulário de recarga via PIX
    $('#recharge-form').on('submit', function(e) {
        e.preventDefault();

        let rawValue = $('#amount').maskMoney('unmasked')[0];
        let amountInCents = parseInt(rawValue * 100);

        const formData = new FormData();
        formData.append('amount', amountInCents);

        const xhr = new XMLHttpRequest();
        xhr.open('POST', $(this).attr('action'), true);

        xhr.onload = function () {
            if (xhr.status === 200) {
                const response = JSON.parse(xhr.responseText);
                if (response.qr_code) {
                    const qrCodeImg = document.getElementById('qr-code');
                    qrCodeImg.src = response.qr_code;
                    qrCodeImg.style.display = 'block';
                    document.getElementById('payment-status').textContent = 'Aguardando pagamento...';
                } else if (response.error) {
                    alert(response.error);
                }
            } else {
                alert('Erro ao gerar o código PIX.');
            }
        };

        xhr.send(formData);
    });

    // Função de upload de arquivo
    $('#uploadForm').on('submit', function(e) {
        e.preventDefault();

        const formData = new FormData(this);
        const xhr = new XMLHttpRequest();

        xhr.open('POST', $(this).attr('action'), true);

        xhr.onload = function () {
            if (xhr.status === 200) {
                const response = JSON.parse(xhr.responseText);
                if (response.success) {
                    alert(response.message);
                    window.location.reload();  // Recarrega a página após sucesso
                } else {
                    alert('Saldo insuficiente! Gerando PIX...');
                    showPixModal(response.file_id, response.custo);
                }
            } else {
                alert('Erro no upload.');
            }
        };

        xhr.send(formData);
    });
});

function showPixModal(fileId, cost) {
    document.getElementById('modalPixAmount').textContent = `R$ ${cost.toFixed(2).replace('.', ',')}`;
    document.getElementById('confirmPixBtn').onclick = function() {
        generatePix(fileId, cost);
    };

    const pixModal = new bootstrap.Modal(document.getElementById('pixModal'));
    pixModal.show();
}

function generatePix(fileId, amountInCents) {
    const xhr = new XMLHttpRequest();
    xhr.open('POST', `/generate_pix/${fileId}`, true);
    xhr.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');
    xhr.onload = function () {
        if (xhr.status === 200) {
            const response = JSON.parse(xhr.responseText);
            if (response.qr_code) {
                alert('PIX gerado com sucesso!');
                window.location.reload();
            } else {
                alert('Erro ao gerar o PIX.');
            }
        } else {
            alert('Erro ao processar a requisição.');
        }
    };
    xhr.send(`custo=${amountInCents}`);  // Envia o valor em centavos para a API
}