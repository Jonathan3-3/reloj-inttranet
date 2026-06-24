from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Q
from .models import TipoIncidencia, RegistroIncidencia
from apps.empleados.models import Empleado


@login_required
def lista_incidencias(request):
    tipo = request.GET.get('tipo', '')
    empleado = request.GET.get('empleado', '')
    justificada = request.GET.get('justificada', '')

    qs = RegistroIncidencia.objects.select_related('empleado', 'tipo', 'atendida_por')

    if tipo:
        qs = qs.filter(tipo__codigo=tipo)
    if empleado:
        qs = qs.filter(Q(empleado__id_original__icontains=empleado) |
                       Q(empleado__nombre__icontains=empleado))
    if justificada in ('si', 'no'):
        qs = qs.filter(justificada=(justificada == 'si'))

    qs = qs.order_by('-fecha', '-creado_en')[:100]

    tipos = TipoIncidencia.objects.all().order_by('orden', 'codigo')

    return render(request, 'incidencias/lista.html', {
        'incidencias': qs,
        'tipos': tipos,
        'filtro_tipo': tipo,
        'filtro_empleado': empleado,
        'filtro_justificada': justificada,
    })


@login_required
@staff_member_required
def lista_tipos(request):
    tipos = TipoIncidencia.objects.all().order_by('orden', 'codigo')
    return render(request, 'incidencias/tipos.html', {'tipos': tipos})


@login_required
@staff_member_required
def nueva_incidencia(request):
    if request.method == 'POST':
        empleado_id = request.POST.get('empleado')
        tipo_id = request.POST.get('tipo')
        fecha = request.POST.get('fecha')
        minutos = request.POST.get('minutos', 0)
        descripcion = request.POST.get('descripcion', '')

        empleado = get_object_or_404(Empleado, pk=empleado_id)
        tipo = get_object_or_404(TipoIncidencia, pk=tipo_id)

        RegistroIncidencia.objects.create(
            empleado=empleado,
            tipo=tipo,
            fecha=fecha,
            minutos=minutos,
            descripcion=descripcion,
            atendida_por=request.user,
        )
        messages.success(request, 'Incidencia registrada correctamente.')
        return redirect('lista-incidencias')

    empleados = Empleado.objects.filter(estatus='activo').order_by('nombre')
    tipos = TipoIncidencia.objects.all().order_by('orden', 'codigo')

    return render(request, 'incidencias/nuevo.html', {
        'empleados': empleados,
        'tipos': tipos,
    })


@login_required
@staff_member_required
def justificar_incidencia(request, pk):
    incidencia = get_object_or_404(RegistroIncidencia, pk=pk)

    if request.method == 'POST':
        incidencia.justificada = True
        incidencia.justificacion = request.POST.get('justificacion', '')
        incidencia.atendida_por = request.user
        incidencia.save()
        messages.success(request, 'Incidencia justificada correctamente.')
        return redirect('lista-incidencias')

    return render(request, 'incidencias/justificar.html', {
        'incidencia': incidencia,
    })


def api_tipos_incidencia(request):
    tipos = TipoIncidencia.objects.all().order_by('orden', 'codigo')
    return JsonResponse({
        'tipos': [{'codigo': t.codigo, 'nombre': t.nombre, 'color': t.color,
                    'es_automatica': t.es_automatica} for t in tipos]
    })


def api_incidencias_empleado(request, empleado_pk):
    incidencias = RegistroIncidencia.objects.filter(
        empleado_id=empleado_pk
    ).select_related('tipo').order_by('-fecha')[:50]

    return JsonResponse({
        'incidencias': [{
            'id': i.id,
            'tipo': i.tipo.codigo,
            'tipo_nombre': i.tipo.nombre,
            'color': i.tipo.color,
            'fecha': i.fecha.isoformat(),
            'minutos': i.minutos,
            'justificada': i.justificada,
        } for i in incidencias]
    })
