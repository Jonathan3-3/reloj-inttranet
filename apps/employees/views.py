import csv
import io
from datetime import date
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Q
from .models import Empleado
from apps.company.models import Area, Departamento
from apps.attendance.calculators.engine import recalcular_asistencia


@login_required
def lista_empleados(request):
    estatus = request.GET.get('estatus', '')
    departamento = request.GET.get('departamento', '')
    q = request.GET.get('q', '')

    qs = Empleado.objects.select_related('departamento', 'user')

    if estatus:
        qs = qs.filter(estatus=estatus)
    if departamento:
        qs = qs.filter(departamento_id=departamento)
    if q:
        qs = qs.filter(Q(id_original__icontains=q) | Q(nombre__icontains=q))

    qs = qs.order_by('nombre')

    departamentos = Departamento.objects.all().select_related('area').order_by('area__nombre', 'nombre')

    return render(request, 'employees/list.html', {
        'empleados': qs,
        'departamentos': departamentos,
        'filtro_estatus': estatus,
        'filtro_departamento': departamento,
        'filtro_q': q,
    })


@login_required
def detalle_empleado(request, pk):
    empleado = get_object_or_404(Empleado.objects.select_related('departamento', 'user'), pk=pk)
    return render(request, 'employees/detail.html', {
        'empleado': empleado,
    })


@login_required
@staff_member_required
def nuevo_empleado(request):
    if request.method == 'POST':
        id_original = request.POST.get('id_original', '').strip().upper()
        nombre = request.POST.get('nombre', '').strip()
        departamento_id = request.POST.get('departamento')
        puesto = request.POST.get('puesto', '')
        telefono = request.POST.get('telefono', '')
        email = request.POST.get('email', '')
        fecha_ingreso = request.POST.get('fecha_ingreso') or None
        id_en_dispositivo = request.POST.get('id_en_dispositivo', '')

        if not id_original or not nombre:
            messages.error(request, 'ID original y nombre son obligatorios.')
            return redirect('nuevo-empleado')

        if Empleado.objects.filter(id_original=id_original).exists():
            messages.error(request, f'El ID {id_original} ya existe.')
            return redirect('nuevo-empleado')

        departamento = None
        if departamento_id:
            departamento = get_object_or_404(Departamento, pk=departamento_id)

        Empleado.objects.create(
            id_original=id_original,
            nombre=nombre,
            departamento=departamento,
            puesto=puesto,
            telefono=telefono,
            email=email,
            fecha_ingreso=fecha_ingreso,
            id_en_dispositivo=id_en_dispositivo or id_original,
        )

        messages.success(request, f'Empleado {nombre} creado correctamente.')
        return redirect('lista-empleados')

    departamentos = Departamento.objects.all().select_related('area').order_by('area__nombre', 'nombre')
    return render(request, 'employees/form.html', {
        'departamentos': departamentos,
        'titulo': 'Nuevo Empleado',
    })


@login_required
@staff_member_required
def editar_empleado(request, pk):
    empleado = get_object_or_404(Empleado, pk=pk)

    if request.method == 'POST':
        empleado.id_original = request.POST.get('id_original', empleado.id_original).strip().upper()
        empleado.nombre = request.POST.get('nombre', empleado.nombre).strip()
        depto_id = request.POST.get('departamento')
        empleado.departamento = get_object_or_404(Departamento, pk=depto_id) if depto_id else None
        empleado.puesto = request.POST.get('puesto', '')
        empleado.telefono = request.POST.get('telefono', '')
        empleado.email = request.POST.get('email', '')
        empleado.fecha_ingreso = request.POST.get('fecha_ingreso') or None
        empleado.id_en_dispositivo = request.POST.get('id_en_dispositivo', '')
        empleado.save()

        messages.success(request, 'Empleado actualizado correctamente.')
        return redirect('lista-empleados')

    departamentos = Departamento.objects.all().select_related('area').order_by('area__nombre', 'nombre')
    return render(request, 'employees/form.html', {
        'empleado': empleado,
        'departamentos': departamentos,
        'titulo': 'Editar Empleado',
    })


@login_required
@staff_member_required
def renuncia_empleado(request, pk):
    empleado = get_object_or_404(Empleado, pk=pk)

    if request.method == 'POST':
        fecha_renuncia = request.POST.get('fecha_renuncia') or date.today()
        empleado.estatus = 'renuncia'
        empleado.fecha_renuncia = fecha_renuncia
        empleado.save()
        messages.success(request, f'{empleado.nombre} marcado como renuncia.')
        return redirect('lista-empleados')

    return render(request, 'employees/resign.html', {
        'empleado': empleado,
    })


@login_required
@staff_member_required
def recontratar_empleado(request, pk):
    empleado = get_object_or_404(Empleado, pk=pk)

    if request.method == 'POST':
        empleado.estatus = 'activo'
        empleado.fecha_recontratacion = date.today()
        empleado.fecha_renuncia = None
        empleado.save()
        messages.success(request, f'{empleado.nombre} recontratado exitosamente.')
        return redirect('lista-empleados')

    return render(request, 'employees/reactivate.html', {
        'empleado': empleado,
    })


@login_required
@staff_member_required
def importar_csv(request):
    if request.method == 'POST' and request.FILES.get('archivo'):
        archivo = request.FILES['archivo']
        decoded = archivo.read().decode('utf-8-sig')
        reader = csv.DictReader(io.StringIO(decoded))

        creados = 0
        actualizados = 0
        errores = 0

        for row in reader:
            try:
                id_orig = row.get('id_original', '').strip().upper()
                nombre = row.get('nombre', '').strip()
                if not id_orig or not nombre:
                    errores += 1
                    continue

                _, created = Empleado.objects.update_or_create(
                    id_original=id_orig,
                    defaults={
                        'nombre': nombre,
                        'puesto': row.get('puesto', ''),
                        'telefono': row.get('telefono', ''),
                        'email': row.get('email', ''),
                    }
                )
                if created:
                    creados += 1
                else:
                    actualizados += 1
            except Exception:
                errores += 1

        messages.success(
            request,
            f'Importación completada: {creados} creados, {actualizados} actualizados, {errores} errores'
        )
        return redirect('lista-empleados')

    return render(request, 'employees/import.html')


def buscar_empleados_api(request):
    q = request.GET.get('q', '')
    empleados = Empleado.objects.filter(estatus='activo')
    if q:
        empleados = empleados.filter(
            Q(id_original__icontains=q) | Q(nombre__icontains=q)
        )
    empleados = empleados.order_by('nombre')[:20]

    return JsonResponse({
        'empleados': [{
            'id': e.id,
            'id_original': e.id_original,
            'nombre': e.nombre,
            'departamento': str(e.departamento or ''),
        } for e in empleados]
    })
