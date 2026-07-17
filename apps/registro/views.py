import json
import uuid
import re
import logging
from django.conf import settings
from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q
from django.db import connection as db_connection
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
        'hora': timezone.localtime(ahora).strftime('%H:%M:%S'),
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


def _formatear_comando_usuario(empleado, cmd_id=1):
    pin_numerico = ''.join(re.findall(r'\d+', empleado.id_original))
    if not pin_numerico:
        pin_numerico = str(empleado.id)
    else:
        pin_numerico = str(int(pin_numerico))

    pri_map = {'superadmin': '14', 'admin': '0', 'empleado': '0'}
    pri = pri_map.get(empleado.tipo_empleado, '0')
    name = (empleado.nombre_completo or empleado.id_original).lower().replace(' ', '_')

    campos_comunes = '\t'.join([
        f'PIN={pin_numerico}',
        f'Name={name}',
        f'Pri={pri}',
        'Passwd=',
        'Card=',
        'Grp=1',
        'TZ=0000000100000000',
    ])

    extras = '\t'.join([
        'VerifyMode=0',
        'ViceCard=',
        'StartDatetime=0',
        'EndDatetime=0',
    ])

    return f'UPDATE USERINFO {campos_comunes}\t{extras}'


def _push_pendientes_a_scanner(sn, start_cmd_id=1):
    """Envía los empleados pendientes de push al escáner.
    Retorna una tupla (lista_de_comandos, siguiente_cmd_id) o (None, start_cmd_id) si no hay pendientes.
    """
    from apps.empleados.models import Empleado

    pendientes_qs = Empleado.objects.filter(pendiente_push=True, estatus='activo')
    if 'sqlite' in db_connection.settings_dict['ENGINE']:
        pendientes = list(pendientes_qs[:100])
    else:
        pendientes = list(pendientes_qs.select_for_update(skip_locked=True)[:100])
    if not pendientes:
        return None, start_cmd_id

    comandos = []
    emp_ids = []
    cmd_id = start_cmd_id
    for emp in pendientes:
        comandos.append(_formatear_comando_usuario(emp, cmd_id))
        emp_ids.append(emp.id)
        cmd_id += 1
    Empleado.objects.filter(id__in=emp_ids).update(pendiente_push=False)
    logger.info(f'Push: {len(comandos)} empleados enviados a SN={sn}')
    return comandos, cmd_id


@csrf_exempt
def _verificar_ip_dispositivo(request):
    ip = request.META.get('HTTP_X_REAL_IP') or request.META.get('REMOTE_ADDR', '')
    if not settings.ALLOWED_DEVICE_IPS:
        logger.error('ALLOWED_DEVICE_IPS no configurado. Acceso denegado desde %s', ip)
        return False
    if ip not in settings.ALLOWED_DEVICE_IPS:
        logger.warning('Acceso denegado a /iclock/ desde %s', ip)
        return False
    return True


def iclock_getrequest(request):
    if not _verificar_ip_dispositivo(request):
        return HttpResponse('FORBIDDEN', content_type='text/plain', status=403)
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

    comandos, _ = _push_pendientes_a_scanner(sn)
    if comandos:
        ahora = timezone.localtime().strftime('%Y-%m-%d %H:%M:%S')
        opstamp = request.GET.get('OpStamp', request.GET.get('opstamp', request.GET.get('Stamp', request.GET.get('stamp', '0'))))
        header = f'OK: timestamp={ahora}&opstamp={opstamp}'
        respuesta = header + '\n' + '\n'.join(comandos)
        logger.info(f'GetRequest push a SN={sn}: {len(comandos)} comandos, {len(respuesta)} bytes')
        for i, cmd in enumerate(comandos):
            logger.info(f'  Cmd {i+1}: {cmd[:120]}...')
        return HttpResponse(respuesta, content_type='text/plain')

    ahora = timezone.localtime().strftime('%Y-%m-%d %H:%M:%S')
    return HttpResponse(f'OK: timestamp={ahora}&opstamp=0', content_type='text/plain')


def _procesar_linea_user(linea, sn, ip):
    """Procesa una línea USER del escáner: USER PIN=X\tName=X\t...
    Crea o actualiza el Empleado correspondiente.
    Retorna True si se procesó correctamente.
    """
    try:
        partes = linea.replace('\t', ' ').split()
        if len(partes) < 2:
            return False
        kv = {}
        for p in partes[1:]:
            if '=' in p:
                k, v = p.split('=', 1)
                kv[k.upper()] = v
        pin = kv.get('PIN', '')
        if not pin:
            return False
        name = kv.get('NAME', '')
        pri = kv.get('PRI', '0')

        empleado = Empleado.objects.filter(
            Q(id_en_dispositivo=pin) | Q(id_original=pin)
        ).first()

        if empleado:
            if name:
                parts_name = name.split(' ', 1)
                nuevo_nombre = parts_name[0]
                nuevos_apellidos = parts_name[1] if len(parts_name) > 1 else ''
                dirty = False
                if empleado.nombre != nuevo_nombre or empleado.apellidos != nuevos_apellidos:
                    empleado.nombre = nuevo_nombre
                    empleado.apellidos = nuevos_apellidos
                    dirty = True
                if not empleado.id_en_dispositivo:
                    empleado.id_en_dispositivo = pin
                    dirty = True
                if dirty:
                    empleado.save()
            return True

        parts_name = name.split(' ', 1) if name else [pin, '']
        id_orig = pin
        if Empleado.objects.filter(id_original=id_orig).exists():
            sufijo = 1
            while Empleado.objects.filter(id_original=f'{id_orig}_{sufijo}').exists():
                sufijo += 1
            id_orig = f'{id_orig}_{sufijo}'

        Empleado.objects.create(
            id_original=id_orig,
            id_en_dispositivo=pin,
            nombre=parts_name[0] if name else pin,
            apellidos=parts_name[1] if len(parts_name) > 1 and name else '',
            estatus='activo',
            tipo_empleado='empleado',
            tipo_verificacion_scanner='facial',
        )
        logger.info(f'Empleado auto-creado desde escáner: PIN={pin} Name={name}')
        return True
    except Exception as e:
        logger.error(f'Error procesando USER: {e}', exc_info=True)
        return False


def _procesar_linea_attlog(pin, fecha_str, sn, ip):
    """Procesa una marcación (ATTLOG) del escáner."""
    try:
        if not pin or not fecha_str:
            return False

        empleado = Empleado.objects.filter(
            Q(id_en_dispositivo=pin) | Q(id_original=pin)
        ).filter(estatus='activo').first()
        if not empleado:
            logger.warning(f'ATTLOG PIN={pin} no encontrado — descartado')
            return False

        fmt = '%Y-%m-%d %H:%M:%S'
        try:
            marcado_en = datetime.strptime(fecha_str, fmt)
        except ValueError:
            try:
                fmt = '%Y/%m/%d %H:%M:%S'
                marcado_en = datetime.strptime(fecha_str, fmt)
            except ValueError:
                return False

        if timezone.is_naive(marcado_en):
            marcado_en = timezone.make_aware(marcado_en, timezone=timezone.get_current_timezone())

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
            recalcular_asistencia(empleado, marcado_en.date())
            return True
        return True
    except Exception as e:
        logger.error(f'Error en ATTLOG: {e}', exc_info=True)
        return False


@csrf_exempt
def iclock_cdata(request):
    if not _verificar_ip_dispositivo(request):
        return HttpResponse('FORBIDDEN', content_type='text/plain', status=403)
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

    for line in body.replace('\r\n', '\n').split('\n'):
        line = line.strip()
        if not line:
            continue

        if line.startswith('USER\t') or line.startswith('USER '):
            if _procesar_linea_user(line, sn, ip):
                procesadas += 1
            else:
                errores += 1
        elif line.startswith('FP\t') or line.startswith('FP '):
            logger.info(f'FP recibido de {ip} — pendiente de almacenar')
            procesadas += 1
        elif line.startswith('OPLOG'):
            pass
        else:
            parts = [p.strip() for p in line.replace('\t', ',').split(',')]
            if len(parts) >= 2:
                pin = parts[0]
                fecha_str = parts[1]
                if _procesar_linea_attlog(pin, fecha_str, sn, ip):
                    procesadas += 1
                else:
                    errores += 1
            else:
                errores += 1

    logger.info(f'CDATA procesadas={procesadas} errores={errores}')
    ahora = timezone.localtime().strftime('%Y-%m-%d %H:%M:%S')
    opstamp = request.GET.get('OpStamp', request.GET.get('opstamp', request.GET.get('Stamp', request.GET.get('stamp', '0'))))
    return HttpResponse(f'OK: timestamp={ahora}&opstamp={opstamp}', content_type='text/plain')


@csrf_exempt
def iclock_device(request):
    if not _verificar_ip_dispositivo(request):
        return HttpResponse('FORBIDDEN', content_type='text/plain', status=403)
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
