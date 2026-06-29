import logging
from datetime import date
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from .models import Horario, Turno, Descanso, AsignacionHorario, ExcepcionHorario
from apps.organizacion.models import Area, Departamento
from apps.empleados.models import Empleado
from apps.asistencia.calculators.engine import obtener_horario_empleado

logger = logging.getLogger(__name__)


@login_required
@staff_member_required
def lista_horarios(request):
    tab = request.GET.get('tab', 'horarios')
    horarios = Horario.objects.all().order_by('nombre')
    turnos = Turno.objects.all().order_by('nombre')
    descansos = Descanso.objects.all().order_by('nombre')
    return render(request, 'horarios/lista.html', {
        'horarios': horarios,
        'turnos': turnos,
        'descansos': descansos,
        'active_tab': tab,
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
