import json
import uuid
from datetime import date
from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.db import transaction
from .models import ConexionWeb
from apps.asistencia.models import Marcacion
from apps.asistencia.calculators.engine import recalcular_asistencia
from apps.empleados.models import Empleado


def checkin_view(request):
    empleados = Empleado.objects.filter(estatus='activo').order_by('nombre')
    empleado_actual = getattr(request.user, 'empleado', None)
    return render(request, 'registro/marcar.html', {
        'empleados': empleados,
        'empleado_actual': empleado_actual,
    })


@csrf_exempt
def api_register(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido'}, status=400)

    empleado_id = data.get('empleado_id')
    accion = data.get('accion', 'entrada')
    lat = data.get('lat')
    lng = data.get('lng')

    empleado = Empleado.objects.filter(id_original=empleado_id, estatus='activo').first()
    if not empleado:
        empleado = Empleado.objects.filter(pk=empleado_id, estatus='activo').first()
    if not empleado:
        return JsonResponse({'error': 'Empleado no encontrado'}, status=404)

    user_agent = request.META.get('HTTP_USER_AGENT', '')
    ip = request.META.get('REMOTE_ADDR', '')

    tipo_dispositivo = 'movil' if any(
        kw in user_agent.lower() for kw in ['mobile', 'android', 'iphone', 'ipad']
    ) else 'pc'

    ahora = timezone.now()

    # Registrar marcación
    marcacion = Marcacion.objects.create(
        empleado=empleado,
        marcado_en=ahora,
        tipo=accion,
        fuente='web',
        ubicacion_lat=lat,
        ubicacion_lng=lng,
        ip_address=ip,
        user_agent=user_agent,
    )

    # Registrar/actualizar conexión web activa
    session_id = data.get('session_id', str(uuid.uuid4()))

    import re
    navegador = 'Desconocido'
    ua = user_agent.lower()
    if 'chrome' in ua and 'edg' not in ua:
        navegador = 'Chrome'
    elif 'firefox' in ua:
        navegador = 'Firefox'
    elif 'safari' in ua:
        navegador = 'Safari'
    elif 'edg' in ua:
        navegador = 'Edge'

    ConexionWeb.objects.update_or_create(
        session_id=session_id,
        defaults={
            'empleado': empleado,
            'ip_address': ip,
            'user_agent': user_agent,
            'tipo_dispositivo': tipo_dispositivo,
            'navegador': navegador,
            'ubicacion_lat': lat,
            'ubicacion_lng': lng,
            'activa': True,
        }
    )

    # Recalcular asistencia
    recalcular_asistencia(empleado, ahora.date())

    return JsonResponse({
        'ok': True,
        'marcacion_id': marcacion.id,
        'hora': ahora.strftime('%H:%M:%S'),
        'session_id': session_id,
        'accion': accion,
        'tipo_dispositivo': tipo_dispositivo,
    })


@csrf_exempt
def api_ping(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido'}, status=400)

    session_id = data.get('session_id')
    if session_id:
        ConexionWeb.objects.filter(session_id=session_id, activa=True).update(
            ultimo_ping=timezone.now(),
            ubicacion_lat=data.get('lat'),
            ubicacion_lng=data.get('lng'),
        )

    return JsonResponse({'ok': True, 'server_time': timezone.now().isoformat()})
