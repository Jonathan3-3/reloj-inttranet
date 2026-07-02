import json
import uuid
import re
import logging
from datetime import datetime
import datetime as dt
from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q
from django.utils import timezone
from .models import ConexionWeb
from apps.asistencia.models import Marcacion
from apps.asistencia.calculators.engine import recalcular_asistencia
from apps.empleados.models import Empleado

logger = logging.getLogger(__name__)


def validar_dispositivo_push(sn, ip):
    """Valida que el serial e IP correspondan a un dispositivo registrado.
    Auto-registra dispositivos desconocidos (primera conexión) con una advertencia.
    """
    from apps.dispositivos.models import Dispositivo
    if not sn:
        return False
    dispositivo = Dispositivo.objects.filter(serial=sn, activo=True).first()
    if not dispositivo:
        logger.warning(f'Primera conexión - auto-registrando dispositivo SN={sn} IP={ip}')
        Dispositivo.objects.update_or_create(
            serial=sn,
            defaults={
                'nombre': f'Scanner {sn}',
                'ip': ip,
                'puerto': 4370,
                'modelo': 'SpeedFace-V3L',
                'tipo': 'scanner',
                'estado': 'online',
                'ultimo_ping': timezone.now(),
                'activo': True,
            }
        )
        return True
    if dispositivo.ip and dispositivo.ip != ip:
        logger.warning(f'IP cambiada para {sn}: {dispositivo.ip} -> {ip}')
        Dispositivo.objects.filter(serial=sn).update(ip=ip)
    return True


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
        'hora': timezone.localtime().strftime('%H:%M:%S'),
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
    ip = request.META.get('REMOTE_ADDR', '')
    options = dict(request.GET)
    logger.info(f'GetRequest from SN={sn} IP={ip} options={options}')
    if not sn:
        return HttpResponse('INVALID SN', content_type='text/plain')
    if not validar_dispositivo_push(sn, ip):
        return HttpResponse('UNAUTHORIZED', content_type='text/plain')

    from apps.dispositivos.models import Dispositivo
    Dispositivo.objects.filter(serial=sn).update(estado='online', ultimo_ping=timezone.now())

    ahora = timezone.localtime().strftime('%Y-%m-%d %H:%M:%S')
    return HttpResponse(f'OK: timestamp={ahora}&opstamp=0', content_type='text/plain')


@csrf_exempt
def iclock_cdata(request):
    sn = request.GET.get('SN', request.GET.get('sn', ''))
    ip = request.META.get('REMOTE_ADDR', '')
    from apps.dispositivos.models import Dispositivo

    if request.method == 'GET':
        if sn and validar_dispositivo_push(sn, ip):
            Dispositivo.objects.filter(serial=sn).update(estado='online', ultimo_ping=timezone.now())
            ahora = timezone.localtime().strftime('%Y-%m-%d %H:%M:%S')
            logger.info(f'CDATA heartbeat from {ip} SN={sn}')
            return HttpResponse(f'OK: timestamp={ahora}&opstamp=0', content_type='text/plain')
        return HttpResponse('OK', content_type='text/plain')

    body = request.body.decode('utf-8', errors='replace')
    logger.info(f'CDATA from {ip} SN={sn} raw=[{body[:500]}]')

    if not sn or not validar_dispositivo_push(sn, ip):
        logger.warning(f'CDATA rechazado: SN={sn} IP={ip}')
        return HttpResponse('UNAUTHORIZED', content_type='text/plain')

    if not body:
        return HttpResponse('OK', content_type='text/plain')

    Dispositivo.objects.filter(serial=sn).update(estado='online', ultimo_ping=timezone.now())

    procesadas = 0
    errores = 0

    records = []
    for line in body.replace('\r\n', '\n').split('\n'):
        line = line.strip()
        if not line:
            continue
        parts = [p.strip() for p in line.replace('\t', ',').split(',')]
        if len(parts) >= 2:
            pin_idx, dt_idx = 0, 1
            if parts[0].startswith('OPLOG'):
                pin_idx, dt_idx = 2, 3
            if len(parts) > max(pin_idx, dt_idx):
                records.append({'PIN': parts[pin_idx], 'DateTime': parts[dt_idx]})

    for rec in records:
        try:
            user_id = rec.get('PIN', '').strip()
            fecha_str = rec.get('DateTime', '').strip()
            if not user_id or not fecha_str:
                continue

            empleado = Empleado.objects.filter(
                Q(id_en_dispositivo=user_id) | Q(id_original=user_id)
            ).filter(estatus='activo').first()
            if not empleado:
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
                marcado_en = timezone.make_aware(marcado_en, timezone=dt.timezone.utc)

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
    ahora = timezone.localtime().strftime('%Y-%m-%d %H:%M:%S')
    opstamp = request.GET.get('OpStamp', request.GET.get('opstamp', request.GET.get('Stamp', request.GET.get('stamp', '0'))))
    return HttpResponse(f'OK: timestamp={ahora}&opstamp={opstamp}', content_type='text/plain')


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
                'ultimo_ping': timezone.now(),
            }
        )

    return HttpResponse('OK', content_type='text/plain')
