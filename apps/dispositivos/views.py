import logging
from datetime import timedelta
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.utils import timezone
from .models import Dispositivo
from .scanner import sincronizar_dispositivo
from apps.registro.models import ConexionWeb

logger = logging.getLogger(__name__)


@staff_member_required
def lista_dispositivos(request):
    dispositivos = Dispositivo.objects.all()
    return render(request, 'dispositivos/lista.html', {
        'dispositivos': dispositivos,
    })


@staff_member_required
def conexiones_activas(request):
    hace_5min = timezone.now() - timedelta(minutes=5)
    conexiones = ConexionWeb.objects.filter(
        activa=True,
        ultimo_ping__gte=hace_5min
    ).select_related('empleado').order_by('-ultimo_ping')

    return render(request, 'dispositivos/conexiones.html', {
        'conexiones': conexiones,
    })


@staff_member_required
def api_estado_dispositivos(request):
    hace_5min = timezone.now() - timedelta(minutes=5)
    dispositivos = Dispositivo.objects.filter(activo=True)

    conexiones_web = ConexionWeb.objects.filter(
        activa=True,
        ultimo_ping__gte=hace_5min
    ).count()

    return JsonResponse({
        'dispositivos': [{
            'id': d.id,
            'nombre': d.nombre,
            'serial': d.serial,
            'ip': d.ip,
            'modelo': d.modelo,
            'estado': d.estado,
            'ultimo_ping': d.ultimo_ping.isoformat() if d.ultimo_ping else None,
            'ultima_sincronizacion': d.ultima_sincronizacion.isoformat() if d.ultima_sincronizacion else None,
        } for d in dispositivos],
        'conexiones_web_activas': conexiones_web,
    })


@staff_member_required
def api_sincronizar(request, pk):
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    dispositivo = get_object_or_404(Dispositivo, pk=pk)

    try:
        resultado = sincronizar_dispositivo(dispositivo)
        return JsonResponse({'ok': True, 'resultado': resultado})
    except Exception as e:
        logger.error(f'Error sincronizando {dispositivo.nombre}: {e}')
        return JsonResponse({'ok': False, 'error': 'Error interno del servidor'}, status=500)
