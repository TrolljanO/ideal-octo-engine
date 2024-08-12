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

function showPixModal(file_id, cost) {
    let costInReais = (cost / 100).toFixed(2);
    document.getElementById('modalPixAmount').textContent = `R$ ${costInReais}`;
    document.getElementById('qrCodeImage').src = '';  // Limpa a imagem antiga do QR Code
    document.getElementById('qrCodeImage').style.display = 'none';  // Esconde a imagem do QR Code
    document.getElementById('qrCodeMessage').textContent = 'Gerando o QR Code...';  // Mensagem enquanto gera o QR Code

    $('#pixModal').modal('show');

    generatePix(file_id, cost);
}

// Adiciona a função de fechamento ao botão "Cancelar" e ao "Close"
document.getElementById('confirmPixBtn').onclick = function () {
    $('#pixModal').modal('hide');  // Fecha o modal
};

document.getElementById('cancelPixBtn').onclick = function () {
    $('#pixModal').modal('hide');  // Fecha o modal
};

function generatePix(fileId, cost) {
    let payload = {
        value: cost,
        correlationID: generateUUID(),
        name: `Pagamento do arquivo ${fileId}`,
        comment: `Pagto arquivo ID ${fileId}`
    };

    const xhr = new XMLHttpRequest();
    xhr.open("POST", `/generate_pix/${fileId}`, true);
    xhr.setRequestHeader("Content-Type", "application/json;charset=UTF-8");
    xhr.onload = function () {
        if (xhr.status === 200) {
            const response = JSON.parse(xhr.responseText);
            if (response.qr_code) {
                document.getElementById('qrCodeImage').src = response.qr_code;
                document.getElementById('qrCodeImage').style.display = 'block';  // Mostra a imagem do QR Code
                document.getElementById('qrCodeMessage').textContent = '';  // Limpa a mensagem
            }
        } else {
            document.getElementById('qrCodeMessage').textContent = 'Erro ao gerar o QR Code. Tente novamente.';
        }
    };
    xhr.send(JSON.stringify(payload));
}


// Função auxiliar para gerar UUID
function generateUUID() {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (c) {
        var r = Math.random() * 16 | 0, v = c == 'x' ? r : (r & 0x3 | 0x8);
        return v.toString(16);
    });
}