import logging
from datetime import date
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Q
from .models import Horario, Turno, Descanso, AsignacionHorario, ExcepcionHorario
from apps.organizacion.models import Area, Departamento
from apps.empleados.models import Empleado
from apps.asistencia.calculators.engine import obtener_horario_empleado

logger = logging.getLogger(__name__)


@login_required
@staff_member_required
def lista_horarios(request):
    tab = request.GET.get('tab', 'horarios')
    sort = request.GET.get('sort', 'nombre')
    dir = request.GET.get('dir', 'asc')
    q = request.GET.get('q', '')

    campos_horario = {
        'nombre': 'nombre',
        'entrada': 'ventana_entrada_inicio',
        'prorroga': 'prorroga_minutos',
        'jornada': 'jornada_hrs',
        'asignacion': 'tipo_asignacion',
    }
    col_h = campos_horario.get(sort, 'nombre')
    if dir == 'desc':
        col_h = '-' + col_h
    horarios = Horario.objects.all()
    if q:
        horarios = horarios.filter(nombre__icontains=q)
    horarios = horarios.order_by(col_h)

    campos_turno = {
        'nombre': 'nombre',
        'entrada': 'entrada_inicio',
        'prorroga': 'prorroga_minutos',
        'tolerancia': 'tolerancia_ausencia_minutos',
        'jornada': 'jornada_hrs',
        'activo': 'activo',
    }
    col_t = campos_turno.get(sort, 'nombre')
    if dir == 'desc':
        col_t = '-' + col_t
    turnos = Turno.objects.all()
    if q:
        turnos = turnos.filter(nombre__icontains=q)
    turnos = turnos.order_by(col_t)

    campos_descanso = {
        'nombre': 'nombre',
        'inicio': 'hora_inicio',
        'fin': 'hora_fin',
        'duracion': 'duracion_minutos',
        'tipo': 'tipo_calculo',
        'activo': 'activo',
    }
    col_d = campos_descanso.get(sort, 'nombre')
    if dir == 'desc':
        col_d = '-' + col_d
    descansos = Descanso.objects.all()
    if q:
        descansos = descansos.filter(nombre__icontains=q)
    descansos = descansos.order_by(col_d)

    return render(request, 'horarios/lista.html', {
        'horarios': horarios,
        'turnos': turnos,
        'descansos': descansos,
        'active_tab': tab,
        'sort': sort,
        'dir': dir,
        'q': q,
    })


@login_required
@staff_member_required
def nuevo_horario(request):
    if request.method == 'POST':
        try:
            horario = Horario.objects.create(
                nombre=request.POST['nombre'],
                ventana_entrada_inicio=request.POST['ventana_entrada_inicio'],
                ventana_entrada_fin=request.POST['ventana_entrada_fin'],
                prorroga_minutos=request.POST.get('prorroga_minutos', 10),
                tolerancia_ausencia_minutos=request.POST.get('tolerancia_ausencia_minutos', 60),
                comida_ventana_inicio=request.POST['comida_ventana_inicio'],
                comida_ventana_fin=request.POST['comida_ventana_fin'],
                comida_duracion_minutos=request.POST.get('comida_duracion_minutos', 60),
                jornada_hrs=request.POST.get('jornada_hrs', 8),
                tipo_asignacion=request.POST['tipo_asignacion'],
            )

            # Asignar áreas/departamentos/empleados según tipo
            if request.POST['tipo_asignacion'] == 'area':
                area_ids = request.POST.getlist('areas')
                horario.areas.set(Area.objects.filter(id__in=area_ids))
            elif request.POST['tipo_asignacion'] == 'departamento':
                depto_ids = request.POST.getlist('departamentos')
                horario.departamentos.set(Departamento.objects.filter(id__in=depto_ids))
            elif request.POST['tipo_asignacion'] == 'individual':
                emp_ids = request.POST.getlist('empleados')
                horario.empleados.set(Empleado.objects.filter(id__in=emp_ids))

            messages.success(request, f'Horario "{horario.nombre}" creado.')
            return redirect('lista-horarios')
        except KeyError as e:
            messages.error(request, f'Campo requerido faltante: {e}')
        except Exception as e:
            logger.error(f'Error creando horario: {e}', exc_info=True)
            messages.error(request, f'Error al crear horario: {e}')

    areas = Area.objects.all()
    departamentos = Departamento.objects.all().select_related('area')
    empleados = Empleado.objects.filter(estatus='activo').order_by('nombre')
    return render(request, 'horarios/formulario.html', {
        'areas': areas,
        'departamentos': departamentos,
        'empleados': empleados,
        'titulo': 'Nuevo Horario',
    })


@login_required
@staff_member_required
def editar_horario(request, pk):
    horario = get_object_or_404(Horario, pk=pk)

    if request.method == 'POST':
        horario.nombre = request.POST['nombre']
        horario.ventana_entrada_inicio = request.POST['ventana_entrada_inicio']
        horario.ventana_entrada_fin = request.POST['ventana_entrada_fin']
        horario.prorroga_minutos = request.POST.get('prorroga_minutos', 10)
        horario.tolerancia_ausencia_minutos = request.POST.get('tolerancia_ausencia_minutos', 60)
        horario.comida_ventana_inicio = request.POST['comida_ventana_inicio']
        horario.comida_ventana_fin = request.POST['comida_ventana_fin']
        horario.comida_duracion_minutos = request.POST.get('comida_duracion_minutos', 60)
        horario.jornada_hrs = request.POST.get('jornada_hrs', 8)
        horario.tipo_asignacion = request.POST['tipo_asignacion']
        horario.activo = request.POST.get('activo') == 'on'
        horario.save()

        messages.success(request, 'Horario actualizado.')
        return redirect('lista-horarios')

    areas = Area.objects.all()
    departamentos = Departamento.objects.all().select_related('area')
    empleados = Empleado.objects.filter(estatus='activo').order_by('nombre')
    return render(request, 'horarios/formulario.html', {
        'horario': horario,
        'areas': areas,
        'departamentos': departamentos,
        'empleados': empleados,
        'titulo': 'Editar Horario',
    })


@login_required
@staff_member_required
def asignar_horario(request, pk):
    horario = get_object_or_404(Horario, pk=pk)

    if request.method == 'POST':
        empleados_ids = request.POST.getlist('empleados')
        fecha_inicio = request.POST.get('fecha_inicio', date.today())
        fecha_fin = request.POST.get('fecha_fin') or None

        for emp_id in empleados_ids:
            AsignacionHorario.objects.update_or_create(
                empleado_id=emp_id,
                fecha_inicio=fecha_inicio,
                defaults={
                    'horario': horario,
                    'fecha_fin': fecha_fin,
                }
            )

        messages.success(request, f'Horario asignado a {len(empleados_ids)} empleados.')
        return redirect('lista-horarios')

    empleados = Empleado.objects.filter(estatus='activo').order_by('nombre')
    return render(request, 'horarios/asignar.html', {
        'horario': horario,
        'empleados': empleados,
    })


@login_required
@staff_member_required
def asignacion_masiva(request):
    horarios = Horario.objects.all().order_by('nombre')
    areas = Area.objects.all()

    if request.method == 'POST':
        horario_id = request.POST.get('horario')
        empleados_ids = request.POST.getlist('empleados')
        fecha_inicio = request.POST.get('fecha_inicio', str(date.today()))
        fecha_fin = request.POST.get('fecha_fin') or None

        if not horario_id or not empleados_ids:
            messages.error(request, 'Selecciona un horario y al menos un empleado.')
            return render(request, 'horarios/asignacion_masiva.html', {
                'horarios': horarios,
                'areas': areas,
            })

        horario = get_object_or_404(Horario, pk=horario_id)
        for emp_id in empleados_ids:
            AsignacionHorario.objects.update_or_create(
                empleado_id=emp_id,
                fecha_inicio=fecha_inicio,
                defaults={
                    'horario': horario,
                    'fecha_fin': fecha_fin,
                }
            )

        messages.success(request, f'Horario "{horario.nombre}" asignado a {len(empleados_ids)} empleados.')
        return redirect('asignacion-masiva')

    return render(request, 'horarios/asignacion_masiva.html', {
        'horarios': horarios,
        'areas': areas,
    })


@login_required
@staff_member_required
def api_departamentos_por_area(request, area_id):
    area = get_object_or_404(Area, pk=area_id)
    departamentos = area.departamentos.all().order_by('nombre')
    data = [{
        'id': d.id,
        'nombre': d.nombre,
        'empleados_count': Empleado.objects.filter(departamento=d, estatus='activo').count(),
    } for d in departamentos]
    return JsonResponse({'departamentos': data})


@login_required
@staff_member_required
def api_empleados_por_filtro(request):
    departamento_ids = request.GET.getlist('departamentos')
    horario_id = request.GET.get('horario_id')
    query = request.GET.get('q', '').strip()
    incluir_con_horario = request.GET.get('incluir_con_horario', 'true') == 'true'

    empleados = Empleado.objects.filter(estatus='activo').select_related('departamento__area')

    if departamento_ids:
        empleados = empleados.filter(departamento_id__in=departamento_ids)

    if query:
        empleados = empleados.filter(
            Q(nombre__icontains=query) |
            Q(apellidos__icontains=query) |
            Q(id_original__icontains=query)
        )

    empleados = empleados.order_by('nombre')
    empleados_ids = list(empleados.values_list('id', flat=True))

    hoy = date.today()
    asignaciones = AsignacionHorario.objects.filter(
        empleado_id__in=empleados_ids,
        fecha_inicio__lte=hoy,
    ).filter(
        Q(fecha_fin__isnull=True) | Q(fecha_fin__gte=hoy)
    ).select_related('horario')

    asignaciones_map = {a.empleado_id: a for a in asignaciones}

    data = []
    for e in empleados:
        asignacion = asignaciones_map.get(e.id)
        if not incluir_con_horario and asignacion:
            continue
        data.append({
            'id': e.id,
            'id_original': e.id_original,
            'nombre': e.nombre_completo,
            'departamento': e.departamento.nombre if e.departamento else '',
            'area': e.departamento.area.nombre if e.departamento and e.departamento.area_id else '',
            'horario_actual': asignacion.horario.nombre if asignacion else None,
            'horario_actual_id': asignacion.horario_id if asignacion else None,
        })

    return JsonResponse({'empleados': data, 'total': len(data)})


@login_required
def api_horario_empleado(request, empleado_pk):
    empleado = get_object_or_404(Empleado, pk=empleado_pk)
    fecha_str = request.GET.get('fecha', str(date.today()))
    try:
        anio, mes, dia = map(int, fecha_str.split('-'))
        fecha = date(anio, mes, dia)
    except (ValueError, TypeError):
        return JsonResponse({'error': 'Fecha inválida'}, status=400)

    horario_info, es_excepcion = obtener_horario_empleado(empleado, fecha)

    if horario_info is None:
        return JsonResponse({'horario': None})

    if es_excepcion:
        return JsonResponse({
            'horario': {
                'tipo': 'excepcion',
                'entrada': str(horario_info.entrada_esperada or ''),
                'salida': str(horario_info.salida_esperada or ''),
                'motivo': horario_info.motivo,
            }
        })

    return JsonResponse({
        'horario': {
            'tipo': 'normal',
            'id': horario_info.id,
            'nombre': horario_info.nombre,
            'entrada_inicio': str(horario_info.ventana_entrada_inicio),
            'entrada_fin': str(horario_info.ventana_entrada_fin),
            'prorroga': horario_info.prorroga_minutos,
            'tolerancia': horario_info.tolerancia_ausencia_minutos,
            'comida_inicio': str(horario_info.comida_ventana_inicio),
            'comida_fin': str(horario_info.comida_ventana_fin),
            'comida_duracion': horario_info.comida_duracion_minutos,
            'jornada_hrs': float(horario_info.jornada_hrs),
        }
    })
