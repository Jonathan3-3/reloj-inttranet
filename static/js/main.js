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

// Encode API text before interpolating it into table cells or Leaflet popups.
function escaparHTML(valor) {
    return String(valor == null ? '' : valor).replace(/[&<>"']/g, function(caracter) {
        return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[caracter];
    });
}

function respuestaAsistencia(response) {
    if (response.redirected || !(response.headers.get('content-type') || '').includes('application/json')) {
        throw new Error('La sesión expiró o el servidor no devolvió una respuesta válida.');
    }
    return response.json().then(function(data) {
        if (!response.ok) throw new Error(data.error || 'No se pudo completar la operación.');
        return data;
    });
}
