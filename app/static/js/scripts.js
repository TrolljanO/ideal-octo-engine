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
            // Exibir o próximo status "Calculando..."
        } else {
            alert('Erro no upload.');
        }
    };

    xhr.send(formData);
});

xhr.onload = function() {
    if (xhr.status === 200) {
        const response = JSON.parse(xhr.responseText);
        const custo = response.custo;
        // Exibir pop-up
        const userConfirmation = confirm(`Valor do processamento: R$ ${custo}`);
        if (userConfirmation) {
            // Enviar confirmação para o servidor
        } else {
            // Cancelar o processo
        }
    } else {
        alert('Erro no upload.');
    }
};

function updateProgressBar(fileId, percentage) {
    const progressBar = document.getElementById(`progress-bar-${fileId}`);
    if (progressBar) {
        progressBar.style.width = `${percentage}%`;
        progressBar.setAttribute('aria-valuenow', percentage);
        progressBar.textContent = `${percentage}%`;
    }
}

function showCostPopup(custo, fileId) {
    if (confirm(`Valor do processamento: R$ ${custo}. Deseja continuar?`)) {
        // Usuário aceitou o custo
        authorizeProcessing(fileId, custo);
    } else {
        // Usuário recusou o custo
        cancelProcessing(fileId);
    }
}

function authorizeProcessing(fileId, custo) {
    fetch('/api/authorize', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ file_id: fileId, custo: custo }),
    }).then(response => response.json())
      .then(data => {
          if (data.status === 'Autorizado') {
              // Continue o processamento
              startProcessing(fileId);
          } else {
              alert('Saldo insuficiente.');
          }
      });
}

function cancelProcessing(fileId) {
    fetch('/api/cancel', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ file_id: fileId }),
    }).then(response => response.json())
      .then(data => {
          alert('Processamento cancelado.');
      });
}

