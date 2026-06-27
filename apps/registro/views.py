import json
import uuid
import re
import logging
from datetime import datetime
from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from .models import ConexionWeb
from apps.asistencia.models import Marcacion
from apps.asistencia.calculators.engine import recalcular_asistencia
from apps.empleados.models import Empleado

logger = logging.getLogger(__name__)


def checkin_view(request):
    empleados = Empleado.objects.filter(estatus='activo').order_by('nombre')
    empleado_actual = getattr(request.user, 'empleado', None)
    return render(request, 'registro/marcar.html', {
        'empleados': empleados,
        'empleado_actual': empleado_actual,
    })


@login_required
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


@login_required
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


@csrf_exempt
def iclock_getrequest(request):
    sn = request.GET.get('SN', request.GET.get('sn', ''))
    if not sn:
        return HttpResponse('INVALID SN', content_type='text/plain')
    logger.info(f'Device request: SN={sn}, options={request.GET}')
    return HttpResponse('OK', content_type='text/plain')


@csrf_exempt
def iclock_cdata(request):
    if request.method != 'POST':
        return HttpResponse('GET: OK', content_type='text/plain')

    sn = request.GET.get('SN', request.GET.get('sn', ''))
    ip = request.META.get('REMOTE_ADDR', '')
    logger.info(f'CDATA from {ip} SN={sn}')

    body = request.body.decode('utf-8', errors='replace')
    if not body:
        return HttpResponse('OK', content_type='text/plain')

    procesadas = 0
    errores = 0

    if request.content_type == 'application/x-www-form-urlencoded':
        records = dict(param.split('=', 1) for param in body.split('&') if '=' in param)
        if 'PIN' in records and 'DateTime' in records:
            records = [records]
        else:
            records = []
    else:
        records = []
        for line in body.split('\n'):
            parts = [p.strip() for p in line.replace('\t', ',').split(',')]
            if len(parts) >= 2 and parts[0].isdigit():
                records.append({'PIN': parts[0], 'DateTime': parts[1]})

    for rec in records:
        try:
            user_id = rec.get('PIN', '').strip()
            fecha_str = rec.get('DateTime', '').strip().replace(' ', ' ')
            if not user_id or not fecha_str:
                continue

            empleado = Empleado.objects.filter(
                id_en_dispositivo=user_id
            ).first()
            if not empleado:
                empleado = Empleado.objects.filter(
                    id_original=user_id
                ).first()
            if not empleado or empleado.estatus != 'activo':
                errores += 1
                continue

            fmt = '%Y-%m-%d %H:%M:%S'
            try:
                marcado_en = datetime.strptime(fecha_str, fmt)
            except ValueError:
                try:
                    fmt = '%Y/%m/%d %H:%M:%S'
                    marcado_en = datetime.strptime(fecha_str, fmt)
                except ValueError:
                    errores += 1
                    continue

            if timezone.is_naive(marcado_en):
                marcado_en = timezone.make_aware(marcado_en)

            _, created = Marcacion.objects.get_or_create(
                empleado=empleado,
                marcado_en=marcado_en,
                defaults={
                    'fuente': 'scanner',
                    'dispositivo_serial': sn,
                    'ip_address': ip,
                }
            )

            if created:
                procesadas += 1
                recalcular_asistencia(empleado, marcado_en.date())
        except Exception as e:
            logger.error(f'Error procesando marcacion: {e}', exc_info=True)
            errores += 1

    logger.info(f'CDATA procesadas={procesadas} errores={errores}')
    return HttpResponse('OK', content_type='text/plain')


@csrf_exempt
def iclock_device(request):
    if request.method == 'POST':
        sn = request.POST.get('SN', request.GET.get('SN', ''))
        ip = request.META.get('REMOTE_ADDR', '')
        logger.info(f'Device register: SN={sn} IP={ip}')

        from apps.dispositivos.models import Dispositivo
        Dispositivo.objects.update_or_create(
            serial=sn,
            defaults={
                'nombre': f'Scanner {sn}',
                'ip': ip,
                'puerto': 4370,
                'modelo': 'SpeedFace-V3L',
                'tipo': 'scanner',
                'estado': 'online',
            }
        )

    return HttpResponse('OK', content_type='text/plain')
