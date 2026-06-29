document.addEventListener('DOMContentLoaded', function() {
    setTimeout(function() {
        document.querySelectorAll('.alert').forEach(function(el) {
            var bsAlert = new bootstrap.Alert(el);
            setTimeout(function() { bsAlert.close(); }, 5000);
        });
    }, 100);
});

function formatearFecha(fecha) {
    if (!fecha) return '';
    var d = new Date(fecha + 'T00:00:00');
    return d.toLocaleDateString('es-MX', {day: '2-digit', month: '2-digit', year: 'numeric'});
}

function mostrarCargando(btn) {
    var original = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Cargando...';
    btn.dataset.original = original;
}

function ocultarCargando(btn) {
    btn.disabled = false;
    btn.innerHTML = btn.dataset.original || 'OK';
}
