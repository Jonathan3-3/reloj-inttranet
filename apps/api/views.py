import json
import logging
from datetime import date, timedelta
from django.contrib.auth import authenticate, login, logout
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.utils import timezone
from django.core.cache import cache
from django.conf import settings
from apps.solicitudes.models import Solicitud, Notificacion
from apps.asistencia.models import Marcacion
from apps.asistencia.calculators.engine import obtener_horario_empleado, clasificar_punches, recalcular_asistencia
from apps.empleados.models import Empleado

logger = logging.getLogger(__name__)

RATE_LIMIT_MAX = 5
RATE_LIMIT_WINDOW = 900  # 15 minutos


@csrf_exempt
def api_login(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)
    try:
        data = json.loads(request.body)
        username = data.get('username', '')
        password = data.get('password', '')
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido'}, status=400)

    if not username or not password:
        return JsonResponse({'error': 'Usuario y contraseña requeridos'}, status=400)

    ip = request.META.get('REMOTE_ADDR', '')
    cache_key = f'login_fail_{ip}'
    attempts = cache.get(cache_key, 0)

    if attempts >= RATE_LIMIT_MAX:
        logger.warning(f'Login rate limit excedido desde {ip} para usuario {username}')
        return JsonResponse({'error': 'Demasiados intentos. Intenta en 15 minutos.'}, status=429)

    user = authenticate(request, username=username, password=password)
    if user is None:
        cache.set(cache_key, attempts + 1, RATE_LIMIT_WINDOW)
        logger.warning(f'Login fallido para usuario {username} desde {ip} (intento {attempts + 1}/{RATE_LIMIT_MAX})')
        return JsonResponse({'error': 'Credenciales inválidas'}, status=401)

    cache.delete(cache_key)
    login(request, user)

    empleado = getattr(user, 'empleado', None)
    return JsonResponse({
        'ok': True,
        'debe_cambiar_password': user.debe_cambiar_password,
        'usuario': {
            'id': user.id,
            'username': user.username,
            'nombre': user.get_full_name(),
            'rol': user.rol,
        },
        'empleado': {
            'id': empleado.id if empleado else None,
            'id_original': empleado.id_original if empleado else None,
            'nombre_completo': empleado.nombre_completo if empleado else '',
        } if empleado else None,
    })


@login_required
def api_me(request):
    user = request.user
    empleado = getattr(user, 'empleado', None)
    return JsonResponse({
        'usuario': {
            'id': user.id,
            'username': user.username,
            'nombre': user.get_full_name(),
            'rol': user.rol,
            'debe_cambiar_password': user.debe_cambiar_password,
        },
        'empleado': {
            'id': empleado.id if empleado else None,
            'id_original': empleado.id_original if empleado else None,
            'nombre_completo': empleado.nombre_completo if empleado else '',
            'departamento': str(empleado.departamento) if empleado and empleado.departamento else '',
            'foto_url': empleado.foto.url if empleado and empleado.foto else None,
        } if empleado else None,
    })


@login_required
def api_cambiar_password(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)
    try:
        data = json.loads(request.body)
        password_nueva = data.get('password_nueva', '')
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido'}, status=400)

    if not password_nueva:
        return JsonResponse({'error': 'La nueva contraseña es requerida'}, status=400)

    if len(password_nueva) < 8:
        return JsonResponse({'error': 'La nueva contraseña debe tener al menos 8 caracteres'}, status=400)

    if not any(c.isupper() for c in password_nueva):
        return JsonResponse({'error': 'La contraseña debe contener al menos una mayúscula'}, status=400)

    if not any(c.islower() for c in password_nueva):
        return JsonResponse({'error': 'La contraseña debe contener al menos una minúscula'}, status=400)

    if not any(c.isdigit() for c in password_nueva):
        return JsonResponse({'error': 'La contraseña debe contener al menos un número'}, status=400)

    request.user.set_password(password_nueva)
    request.user.debe_cambiar_password = False
    request.user.save()

    from django.contrib.auth import update_session_auth_hash
    update_session_auth_hash(request, request.user)

    return JsonResponse({'ok': True, 'mensaje': 'Contraseña actualizada correctamente'})


@login_required
def api_logout(request):
    logout(request)
    return JsonResponse({'ok': True})


@login_required
def api_solicitudes(request):
    empleado = getattr(request.user, 'empleado', None)
    if not empleado:
        return JsonResponse({'error': 'Sin empleado vinculado'}, status=400)

    if request.method == 'GET':
        qs = Solicitud.objects.filter(empleado=empleado).order_by('-creado_en')
        return JsonResponse({
            'solicitudes': [{
                'id': s.id,
                'tipo': s.tipo,
                'tipo_display': s.get_tipo_display(),
                'fecha_inicio': s.fecha_inicio.isoformat(),
                'fecha_fin': s.fecha_fin.isoformat(),
                'descripcion': s.descripcion,
                'estatus': s.estatus,
                'comentario_admin': s.comentario_admin,
                'creado_en': s.creado_en.isoformat(),
                'archivo_url': s.archivo.url if s.archivo else None,
            } for s in qs]
        })

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'JSON inválido'}, status=400)

        tipo = data.get('tipo')
        fecha_inicio = data.get('fecha_inicio')
        fecha_fin = data.get('fecha_fin')
        descripcion = data.get('descripcion', '')
        archivo_b64 = data.get('archivo', '')

        if not tipo or not fecha_inicio or not fecha_fin:
            return JsonResponse({'error': 'tipo, fecha_inicio y fecha_fin son requeridos'}, status=400)

        if not archivo_b64:
            return JsonResponse({'error': 'Debe adjuntar un documento'}, status=400)

        import base64, uuid, os
        from django.conf import settings
        from django.core.files.base import ContentFile

        try:
            fmt, b64data = archivo_b64.split(';base64,')
            ext = fmt.split('/')[-1].split(';')[0].split('+')[0]
            if ext not in ('pdf', 'jpg', 'jpeg', 'png'):
                ext = 'pdf'
        except Exception:
            return JsonResponse({'error': 'Formato de archivo inválido'}, status=400)

        raw = base64.b64decode(b64data)
        header = raw[:8]
        if not any(header.startswith(sig) for sig in (b'%PDF', b'\xFF\xD8\xFF', b'\x89PNG\r\n')):
            return JsonResponse({'error': 'El archivo no es un PDF, JPG o PNG válido'}, status=400)
        if len(raw) > 5 * 1024 * 1024:
            return JsonResponse({'error': 'El archivo no debe exceder 5MB'}, status=400)

        filename = f'solicitud_{uuid.uuid4().hex[:12]}.{ext}'

        solicitud = Solicitud(
            empleado=empleado,
            tipo=tipo,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            descripcion=descripcion,
        )
        solicitud.archivo.save(filename, ContentFile(raw), save=False)
        solicitud.save()

        jefes = Empleado.objects.filter(
            Q(tipo_empleado__in=['admin', 'superadmin']) |
            Q(departamento=empleado.departamento, cargo__isnull=False),
            estatus='activo'
        ).exclude(id=empleado.id).select_related('user')

        for jefe in jefes:
            if jefe.user:
                Notificacion.objects.create(
                    usuario=jefe.user,
                    tipo='solicitud_nueva',
                    titulo=f'Nueva solicitud: {solicitud.get_tipo_display()}',
                    mensaje=f'{empleado.nombre_completo} solicitó {solicitud.get_tipo_display()} del {fecha_inicio} al {fecha_fin}',
                    url='/solicitudes/admin/',
                )

        return JsonResponse({'ok': True, 'id': solicitud.id}, status=201)

    return JsonResponse({'error': 'Método no permitido'}, status=405)


@login_required
def api_checkin_status(request):
    """Devuelve el estado actual del check-in para el empleado logueado.
    Usa el mismo motor (clasificar_punches) que los reportes.
    La app usa esto para saber qué botón mostrar.
    """
    empleado = getattr(request.user, 'empleado', None)
    if not empleado:
        return JsonResponse({'error': 'Sin empleado vinculado'}, status=400)

    hoy = timezone.localtime().date()
    horario_info, es_excepcion = obtener_horario_empleado(empleado, hoy)

    if horario_info is None:
        punches_qs = Marcacion.objects.filter(
            empleado=empleado, marcado_en__date=hoy
        ).order_by('marcado_en')
        total = punches_qs.count()
        entrada = punches_qs.first() if total >= 1 else None
        salida = punches_qs.last() if total >= 2 else None
        comida_inicio = None
        comida_fin = None
        extras = []
        es_secuencial = False
        ultimo = punches_qs.last() if total > 0 else None
    else:
        punches, entrada, comida_inicio, comida_fin, salida, extras, _ = clasificar_punches(
            empleado, hoy, horario_info, es_excepcion
        )
        total = len(punches)
        es_secuencial = not es_excepcion and horario_info.clasificacion_secuencial
        ultimo = punches[-1] if total > 0 else None

    tiene_entrada = entrada is not None
    tiene_salida = salida is not None
    tiene_comida_inicio = comida_inicio is not None
    tiene_comida_fin = comida_fin is not None

    puede_entrada = not tiene_entrada
    puede_salida = tiene_entrada and not tiene_salida
    puede_comida_inicio = tiene_entrada and not tiene_salida and not tiene_comida_inicio
    puede_comida_fin = tiene_comida_inicio and not tiene_comida_fin and not tiene_salida

    if total == 0:
        accion, label = 'entrada', 'Marcar Entrada'
    elif not tiene_entrada:
        accion, label = 'entrada', 'Marcar Entrada'
    elif not tiene_salida and es_secuencial and not tiene_comida_inicio:
        accion, label = 'comida_inicio', 'Marcar Comida'
    elif not tiene_salida and es_secuencial and tiene_comida_inicio and not tiene_comida_fin:
        accion, label = 'comida_fin', 'Regresar de Comida'
    elif not tiene_salida:
        accion, label = 'salida', 'Marcar Salida'
    elif extras:
        extra_count = len(extras)
        extra_num = extra_count // 2 + 1
        if extra_count % 2 == 0:
            accion, label = 'extra_inicio', f'Iniciar Extra #{extra_num}'
        else:
            accion, label = 'extra_fin', f'Terminar Extra #{extra_num}'
    else:
        accion, label = 'completo', 'Jornada completa'

    iso = lambda p: timezone.localtime(p.marcado_en).isoformat() if p else None
    return JsonResponse({
        'total_punches_hoy': total,
        'accion_siguiente': accion,
        'label_boton': label,
        'ultima_marcacion': iso(ultimo) if ultimo else None,
        'tiene_entrada': tiene_entrada,
        'tiene_salida': tiene_salida,
        'tiene_comida_inicio': tiene_comida_inicio,
        'tiene_comida_fin': tiene_comida_fin,
        'puede_entrada': puede_entrada,
        'puede_salida': puede_salida,
        'puede_comida_inicio': puede_comida_inicio,
        'puede_comida_fin': puede_comida_fin,
        'punches': {
            'entrada': iso(entrada),
            'comida_inicio': iso(comida_inicio),
            'comida_fin': iso(comida_fin),
            'salida': iso(salida),
        },
    })
