from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponseForbidden
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Q
from django.utils import timezone
from .models import Solicitud, Notificacion
from apps.empleados.models import Empleado


@login_required
def lista_solicitudes(request):
    empleado = getattr(request.user, 'empleado', None)
    if empleado:
        solicitudes = Solicitud.objects.filter(empleado=empleado).order_by('-creado_en')
    else:
        solicitudes = Solicitud.objects.none()

    return render(request, 'solicitudes/lista.html', {
        'solicitudes': solicitudes,
    })


@login_required
def nueva_solicitud(request):
    empleado = getattr(request.user, 'empleado', None)
    if not empleado:
        messages.error(request, 'Tu usuario no está vinculado a un empleado.')
        return redirect('dashboard')

    if request.method == 'POST':
        tipo = request.POST.get('tipo')
        fecha_inicio = request.POST.get('fecha_inicio')
        fecha_fin = request.POST.get('fecha_fin')
        descripcion = request.POST.get('descripcion', '')
        archivo = request.FILES.get('archivo')

        if not tipo or not fecha_inicio or not fecha_fin:
            messages.error(request, 'Todos los campos obligatorios deben llenarse.')
            return redirect('nueva-solicitud')

        solicitud = Solicitud.objects.create(
            empleado=empleado,
            tipo=tipo,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            descripcion=descripcion,
            archivo=archivo,
        )

        # Notificar a admins y jefes
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

        messages.success(request, 'Solicitud enviada correctamente. Espera la aprobación.')
        return redirect('lista-solicitudes')

    return render(request, 'solicitudes/nuevo.html', {
        'empleado': empleado,
    })


@login_required
def detalle_solicitud(request, pk):
    solicitud = get_object_or_404(Solicitud, pk=pk)
    empleado = getattr(request.user, 'empleado', None)

    if not (request.user.is_staff or (empleado and solicitud.empleado == empleado)):
        return HttpResponseForbidden()

    return render(request, 'solicitudes/detalle.html', {
        'solicitud': solicitud,
    })


@staff_member_required
def panel_admin(request):
    estatus = request.GET.get('estatus', 'pendiente')
    tipo = request.GET.get('tipo', '')

    qs = Solicitud.objects.select_related('empleado__departamento').order_by('-creado_en')

    if estatus:
        qs = qs.filter(estatus=estatus)
    if tipo:
        qs = qs.filter(tipo=tipo)

    return render(request, 'solicitudes/panel_admin.html', {
        'solicitudes': qs,
        'filtro_estatus': estatus,
        'filtro_tipo': tipo,
    })


@staff_member_required
def aprobar_solicitud(request, pk):
    solicitud = get_object_or_404(Solicitud, pk=pk)
    if request.method == 'POST':
        solicitud.aprobar(request.user)
        messages.success(request, f'Solicitud de {solicitud.empleado.nombre_completo} aprobada.')
    return redirect('panel-solicitudes')


@staff_member_required
def rechazar_solicitud(request, pk):
    solicitud = get_object_or_404(Solicitud, pk=pk)
    if request.method == 'POST':
        comentario = request.POST.get('comentario', '')
        solicitud.rechazar(request.user, comentario)
        messages.warning(request, f'Solicitud de {solicitud.empleado.nombre_completo} rechazada.')
    return redirect('panel-solicitudes')


@login_required
def api_notificaciones(request):
    notificaciones = Notificacion.objects.filter(
        Q(usuario=request.user) | Q(empleado__user=request.user),
        leida=False
    ).order_by('-creado_en')[:20]

    return JsonResponse({
        'no_leidas': notificaciones.count(),
        'notificaciones': [{
            'id': n.id,
            'titulo': n.titulo,
            'mensaje': n.mensaje,
            'tipo': n.tipo,
            'url': n.url,
            'creado_en': n.creado_en.isoformat(),
        } for n in notificaciones]
    })


@login_required
def api_marcar_leida(request, pk):
    notif = get_object_or_404(Notificacion, pk=pk)
    if notif.usuario == request.user or (notif.empleado and notif.empleado.user == request.user):
        notif.leida = True
        notif.save()
        return JsonResponse({'ok': True})
    return JsonResponse({'error': 'No autorizado'}, status=403)
