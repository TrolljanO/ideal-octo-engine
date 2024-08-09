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
    $("#navbarNav").on("click", "li", function (e) {
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
    // Get current path and find target link
    var path = window.location.pathname.split("/").pop();

    // Account for home page with empty path
    if (path == '') {
        path = 'index.html';
    }

    var target = $('#navbarNav ul li a[href="' + path + '"]');
    // Add active class to target link
    target.parent().addClass('active');
});

const form = document.querySelector('#uploadForm');
const progressBar = document.querySelector('.progress-bar');

form.addEventListener('submit', function(e) {
    e.preventDefault();
    const formData = new FormData(form);
    const xhr = new XMLHttpRequest();

    xhr.open('POST', form.action, true);

    xhr.upload.onprogress = function(event) {
        if (event.lengthComputable) {
            const percentComplete = (event.loaded / event.total) * 100;
            progressBar.style.width = percentComplete + '%';
            progressBar.setAttribute('aria-valuenow', percentComplete);
            progressBar.textContent = Math.floor(percentComplete) + '%';
        }
    };

        xhr.onload = function() {
            if (xhr.status === 200) {
                const response = JSON.parse(xhr.responseText);
                const custo = response.custo;

                // Exibe o custo e as opções de autorização
                const userConfirmation = confirm(`Valor do processamento: R$ ${custo}. Deseja autorizar?`);
                if (userConfirmation) {
                    // Enviar confirmação para o servidor
                    authorizeProcessing(response.file_id, custo);
                } else {
                    // Cancelar o processo
                    cancelProcessing(response.file_id);
                }
            } else {
                alert('Erro no upload.');
            }
        };


xhr.upload.onprogress = function(event) {
    if (event.lengthComputable) {
        const percentComplete = (event.loaded / event.total) * 100;
        progressBar.style.width = percentComplete + '%';
        progressBar.setAttribute('aria-valuenow', percentComplete);
        progressBar.textContent = Math.floor(percentComplete) + '%';

        // Simulação de processamento
        if (percentComplete === 100) {
            setTimeout(() => {
                progressBar.classList.add('bg-info');
                progressBar.textContent = 'Processando...';
            }, 500); // Aguarde 500ms antes de exibir "Processando..."
        }
    }
};


    xhr.send(formData);
});
