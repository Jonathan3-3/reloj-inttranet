import json
from datetime import date
from django.contrib.auth import authenticate, login, logout
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.utils import timezone
from apps.solicitudes.models import Solicitud, Notificacion
from apps.asistencia.models import Marcacion
from apps.empleados.models import Empleado


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

    user = authenticate(request, username=username, password=password)
    if user is None:
        return JsonResponse({'error': 'Credenciales inválidas'}, status=401)

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

        if not tipo or not fecha_inicio or not fecha_fin:
            return JsonResponse({'error': 'tipo, fecha_inicio y fecha_fin son requeridos'}, status=400)

        solicitud = Solicitud.objects.create(
            empleado=empleado,
            tipo=tipo,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            descripcion=descripcion,
        )

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
    La app usa esto para saber qué botón mostrar.
    """
    empleado = getattr(request.user, 'empleado', None)
    if not empleado:
        return JsonResponse({'error': 'Sin empleado vinculado'}, status=400)

    hoy = timezone.localtime().date()
    punches_hoy = Marcacion.objects.filter(
        empleado=empleado,
        marcado_en__date=hoy
    ).order_by('marcado_en')

    total = punches_hoy.count()
    if total == 0:
        accion = 'entrada'
        label = 'Marcar Entrada'
    elif total == 1:
        accion = 'comida_inicio'
        label = 'Marcar Comida'
    elif total == 2:
        accion = 'comida_fin'
        label = 'Regresar de Comida'
    elif total == 3:
        accion = 'salida'
        label = 'Marcar Salida'
    else:
        extra_num = (total - 3) // 2 + 1
        if (total - 3) % 2 == 1:
            accion = 'extra_fin'
            label = f'Terminar Extra #{extra_num}'
        else:
            accion = 'extra_inicio'
            label = f'Iniciar Extra #{extra_num}'

    return JsonResponse({
        'total_punches_hoy': total,
        'accion_siguiente': accion,
        'label_boton': label,
        'ultima_marcacion': timezone.localtime(punches_hoy.last().marcado_en).isoformat() if punches_hoy.exists() else None,
    })
