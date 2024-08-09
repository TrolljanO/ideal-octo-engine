// ---------Responsive-navbar-active-animation-----------
function test() {
    var tabsNewAnim = $('#navbarNav');
    var selectorNewAnim = $('#navbarNav').find('li').length;
    var activeItemNewAnim = tabsNewAnim.find('.active');
    var activeWidthNewAnimHeight = activeItemNewAnim.innerHeight();
    var activeWidthNewAnimWidth = activeItemNewAnim.innerWidth();
    var itemPosNewAnimTop = activeItemNewAnim.position();
    var itemPosNewAnimLeft = activeItemNewAnim.position();
    $(".hori-selector").css({
        "top": itemPosNewAnimTop.top + "px",
        "left": itemPosNewAnimLeft.left + "px",
        "height": activeWidthNewAnimHeight + "px",
        "width": activeWidthNewAnimWidth + "px"
    });
    $("#navbarNav").on("click", "li", function () {
        $('#navbarNav ul li').removeClass("active");
        $(this).addClass('active');
        var activeWidthNewAnimHeight = $(this).innerHeight();
        var activeWidthNewAnimWidth = $(this).innerWidth();
        var itemPosNewAnimTop = $(this).position();
        var itemPosNewAnimLeft = $(this).position();
        $(".hori-selector").css({
            "top": itemPosNewAnimTop.top + "px",
            "left": itemPosNewAnimLeft.left + "px",
            "height": activeWidthNewAnimHeight + "px",
            "width": activeWidthNewAnimWidth + "px"
        });
    });
}

$(document).ready(function () {
    setTimeout(function () { test(); });
});

$(window).on('resize', function () {
    setTimeout(function () { test(); }, 500);
});

$(".navbar-toggler").click(function () {
    $(".navbar-collapse").slideToggle(300);
    setTimeout(function () { test(); });
});

// --------------add active class-on another-page move----------
jQuery(document).ready(function ($) {
    var path = window.location.pathname.split("/").pop();
    if (path == '') path = 'index.html';
    var target = $('#navbarNav ul li a[href="' + path + '"]');
    target.parent().addClass('active');
});

// Função de upload de arquivo
const uploadForm = document.querySelector('#uploadForm');
const progressBar = document.querySelector('.progress-bar');

if (uploadForm) {
    uploadForm.addEventListener('submit', function (e) {
        e.preventDefault();
        const formData = new FormData(uploadForm);
        const xhr = new XMLHttpRequest();

        xhr.open('POST', uploadForm.action, true);

        xhr.onload = function () {
            if (xhr.status === 200) {
                try {
                    const response = JSON.parse(xhr.responseText);
                    const custo = response.custo;
                    const fileId = response.file_id;

                    if (confirm(`Valor do processamento: R$ ${custo}. Deseja continuar?`)) {
                        authorizeProcessing(fileId, custo);
                    } else {
                        cancelProcessing(fileId);
                    }
                } catch (e) {
                    alert('Erro ao processar a resposta do servidor.');
                    console.error('Erro ao processar JSON:', e);
                }
            } else {
                alert('Erro no upload.');
            }
        };

        xhr.upload.onprogress = function (event) {
            if (event.lengthComputable) {
                const percentComplete = (event.loaded / event.total) * 100;
                progressBar.style.width = percentComplete + '%';
                progressBar.setAttribute('aria-valuenow', percentComplete);
                progressBar.textContent = Math.floor(percentComplete) + '%';

                if (percentComplete === 100) {
                    setTimeout(() => {
                        progressBar.classList.add('bg-info');
                        progressBar.textContent = 'Processando...';
                    }, 500);
                }
            }
        };

        xhr.send(formData);
    });
}

// Função de recarga via PIX
const rechargeForm = document.querySelector('#recharge-form');
const amountInput = document.getElementById('amount');

$(function() {
    $('#amount').maskMoney({
        prefix: 'R$ ',
        allowNegative: false,
        thousands: '.',
        decimal: ',',
        affixesStay: true,
        precision: 2 // Deixa a precisão em 2 casas decimais
    });

    $('#recharge-form').on('submit', function(e) {
        e.preventDefault();

        // Pega o valor desformatado como número float
        let rawValue = $('#amount').maskMoney('unmasked')[0];

        // Converte o valor para centavos
        let amountInCents = parseInt(rawValue * 100);

        const formData = new FormData();
        formData.append('amount', amountInCents); // Envia o valor em centavos

        const xhr = new XMLHttpRequest();
        xhr.open('POST', $(this).attr('action'), true);

        xhr.onload = function () {
            if (xhr.status === 200) {
                try {
                    const response = JSON.parse(xhr.responseText);
                    if (response.qr_code) {
                        const qrCodeImg = document.getElementById('qr-code');
                        qrCodeImg.src = response.qr_code;
                        qrCodeImg.style.display = 'block';
                        document.getElementById('payment-status').textContent = 'Aguardando pagamento...';
                    } else if (response.error) {
                        alert(response.error);
                    }
                } catch (e) {
                    alert('Erro ao processar a resposta do servidor.');
                }
            } else {
                alert('Erro ao gerar o código PIX.');
            }
        };

        xhr.send(formData);
    });
});


// Função para autorizar processamento
function authorizeProcessing(fileId, custo) {
    const formData = new FormData();
    formData.append('file_id', fileId);

    fetch('/process_authorization', {
        method: 'POST',
        body: formData,
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert('Processamento autorizado!');
            window.location.reload();
        } else {
            alert('Erro: ' + data.message);
        }
    })
    .catch(error => console.error('Erro ao autorizar o processamento:', error));
}

// Função para cancelar processamento
function cancelProcessing(fileId) {
    console.log("Cancelando processamento para o arquivo ID:", fileId);

    const xhr = new XMLHttpRequest();
    xhr.open('POST', '/cancel_process', true);
    xhr.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');
    xhr.onload = function() {
        if (xhr.status === 200) {
            alert('Processo cancelado.');
            window.location.reload();
        } else {
            alert('Erro ao cancelar o processo.');
        }
    };
    xhr.send(`file_id=${fileId}`);
}

// Função para verificar o status do pagamento
function checkPaymentStatus(correlation_id) {
    fetch(`/payment_status?correlation_id=${correlation_id}`)
        .then(response => response.json())
        .then(data => {
            if (data.status === 'paid') {
                alert('Pagamento confirmado!');
                location.reload(); // Recarrega a página
            } else {
                setTimeout(() => checkPaymentStatus(correlation_id), 5000); // Verifica novamente em 5 segundos
            }
        })
        .catch(error => console.error('Erro ao verificar status do pagamento:', error));
}

// Chame a função passando o correlation_id
checkPaymentStatus('<correlation_id_da_transacao>');
