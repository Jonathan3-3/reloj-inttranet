from datetime import time, timedelta, date, datetime
import logging
from django.utils import timezone
from django.db import transaction

logger = logging.getLogger(__name__)

AUSENCIA_CODIGO = 'finj'
RETARDO_CODIGO = 'llt'
EXC_COMIDA_CODIGO = 'exc_comida'


def obtener_horario_empleado(empleado, fecha):
    """Obtiene el horario aplicable a un empleado en una fecha específica.
    Jerarquía: Excepción > Asignación individual > Departamento > Area
    """
    from ..models import AsistenciaDiaria
    from apps.horarios.models import Horario, AsignacionHorario, ExcepcionHorario

    # 1. Verificar excepción
    try:
        exc = ExcepcionHorario.objects.get(empleado=empleado, fecha=fecha)
        return exc, True  # Devuelve la excepción
    except ExcepcionHorario.DoesNotExist:
        pass

    # 2. Asignación individual directa
    asignacion = AsignacionHorario.objects.filter(
        empleado=empleado,
        fecha_inicio__lte=fecha,
    ).exclude(
        fecha_fin__lt=fecha
    ).select_related('horario').order_by('-fecha_inicio').first()

    if asignacion and asignacion.horario.tipo_asignacion == 'individual':
        return asignacion.horario, False

    # 3. Por departamento
    if empleado.departamento:
        horario_depto = Horario.objects.filter(
            departamentos=empleado.departamento,
            tipo_asignacion='departamento',
            activo=True
        ).first()
        if horario_depto:
            return horario_depto, False

    # 4. Por área
    if empleado.departamento and empleado.departamento.area:
        horario_area = Horario.objects.filter(
            areas=empleado.departamento.area,
            tipo_asignacion='area',
            activo=True
        ).first()
        if horario_area:
            return horario_area, False

    return None, False


def clasificar_punches(empleado, fecha, horario_obj, es_excepcion):
    """Clasifica las marcaciones del día en: entrada, comida_inicio, comida_fin, salida"""
    from ..models import Marcacion

    punches = Marcacion.objects.filter(
        empleado=empleado,
        marcado_en__date=fecha
    ).order_by('marcado_en')

    if not punches.exists():
        return punches, None, None, None, None

    if es_excepcion:
        entrada = punches.first()
        salida = punches.last()
        return punches, entrada, None, None, salida

    h_start = horario_obj.ventana_entrada_inicio
    h_end = horario_obj.ventana_entrada_fin
    c_start = horario_obj.comida_ventana_inicio
    c_end = horario_obj.comida_ventana_fin

    entrada = None
    comida_inicio = None
    comida_fin = None
    salida = None

    comidas = []

    for p in punches:
        t = p.marcado_en.time()
        if h_start <= t <= h_end and entrada is None:
            entrada = p
        elif c_start <= t <= c_end:
            comidas.append(p)

    for p in punches:
        if p != entrada and p not in comidas:
            salida = p

    if len(comidas) >= 1:
        comida_inicio = comidas[0]
    if len(comidas) >= 2:
        comida_fin = comidas[1]

    return punches, entrada, comida_inicio, comida_fin, salida


def calcular_retardo(entrada_time, horario_obj):
    """Calcula minutos de retardo según las reglas:
    - Dentro del horario + prórroga -> 0 retardo
    - Después de prórroga pero dentro de tolerancia -> retardo
    - Después de tolerancia -> ausencia
    Retorna: (minutos_retardo, codigo_incidencia)
    """
    if entrada_time is None:
        return 0, 'finj'

    inicio = horario_obj.ventana_entrada_inicio
    prorroga = timedelta(minutes=horario_obj.prorroga_minutos)
    tolerancia = timedelta(minutes=horario_obj.tolerancia_ausencia_minutos)

    inicio_dt = datetime.combine(date.today(), inicio)
    entrada_dt = datetime.combine(date.today(), entrada_time)

    diff = entrada_dt - inicio_dt

    if diff <= prorroga:
        return 0, ''
    elif diff <= tolerancia:
        minutos = int(diff.total_seconds() // 60)
        return minutos, 'llt'
    else:
        return int(diff.total_seconds() // 60), 'finj'


def calcular_comida(comida_inicio_time, comida_fin_time, horario_obj):
    """Calcula si excedió el tiempo de comida.
    Retorna: (minutos_comida, excedido)
    """
    if comida_inicio_time is None or comida_fin_time is None:
        return 0, False

    inicio = datetime.combine(date.today(), comida_inicio_time)
    fin = datetime.combine(date.today(), comida_fin_time)
    diff = fin - inicio
    minutos = int(diff.total_seconds() // 60)

    permitido = horario_obj.comida_duracion_minutos
    return minutos, minutos > permitido


def calcular_horas_jornada(entrada_time, salida_time, comida_minutos):
    """Calcula las horas netas trabajadas en el día."""
    if entrada_time is None or salida_time is None:
        return 0

    entrada_dt = datetime.combine(date.today(), entrada_time)
    salida_dt = datetime.combine(date.today(), salida_time)

    if salida_dt < entrada_dt:
        salida_dt += timedelta(days=1)

    total = salida_dt - entrada_dt
    horas = total.total_seconds() / 3600
    horas -= comida_minutos / 60
    return round(max(0, horas), 2)


@transaction.atomic
def recalcular_asistencia(empleado, fecha):
    """Función principal: recalcula la asistencia de un empleado en una fecha.
    Se ejecuta automáticamente cuando llega una nueva marcación.
    """
    from ..models import AsistenciaDiaria
    from apps.incidencias.models import TipoIncidencia, RegistroIncidencia

    horario_info, es_excepcion = obtener_horario_empleado(empleado, fecha)
    if horario_info is None:
        logger.warning(f'Sin horario para {empleado.id_original} en {fecha}')
        return None

    if es_excepcion:
        entrada_time = horario_info.entrada_esperada
        salida_time = horario_info.salida_esperada
        asistencia, _ = AsistenciaDiaria.objects.update_or_create(
            empleado=empleado, fecha=fecha,
            defaults={
                'horario': None,
                'entrada': entrada_time,
                'salida': salida_time,
                'estatus': 'completo' if (entrada_time and salida_time) else 'pendiente',
                'horas_jornada': 0,
                'minutos_retardo': 0,
                'minutos_extra': 0,
                'minutos_comida': 0,
                'incidencia_codigo': '',
            }
        )
        return asistencia

    horario = horario_info
    punches, entrada, comida_inicio, comida_fin, salida = clasificar_punches(
        empleado, fecha, horario, False
    )

    if not punches.exists():
        ahora = timezone.now()
        if ahora.date() > fecha:
            asistencia, _ = AsistenciaDiaria.objects.update_or_create(
                empleado=empleado, fecha=fecha,
                defaults={
                    'horario': horario,
                    'estatus': 'ausente',
                    'incidencia_codigo': 'finj',
                }
            )
            tipo = TipoIncidencia.objects.filter(codigo=AUSENCIA_CODIGO).first()
            if tipo:
                RegistroIncidencia.objects.get_or_create(
                    empleado=empleado,
                    tipo=tipo,
                    fecha=fecha,
                    defaults={'minutos': 0, 'descripcion': f'Ausencia automática - {fecha}'}
                )
            else:
                logger.warning(f'TipoIncidencia {AUSENCIA_CODIGO} no existe — incidencia no creada para {empleado.id_original}')
            return asistencia
        return None

    entrada_time = entrada.marcado_en.time() if entrada else None
    salida_time = salida.marcado_en.time() if salida else None
    comida_inicio_time = comida_inicio.marcado_en.time() if comida_inicio else None
    comida_fin_time = comida_fin.marcado_en.time() if comida_fin else None

    minutos_retardo, cod_incidencia = calcular_retardo(entrada_time, horario)
    minutos_comida, excedio_comida = calcular_comida(comida_inicio_time, comida_fin_time, horario)
    horas_jornada = calcular_horas_jornada(entrada_time, salida_time, minutos_comida)

    incidencia_final = cod_incidencia or (EXC_COMIDA_CODIGO if excedio_comida else '')

    if entrada_time is None and salida_time is None:
        estatus = 'ausente'
    elif entrada_time and salida_time:
        estatus = 'completo'
    else:
        estatus = 'pendiente'

    asistencia, _ = AsistenciaDiaria.objects.update_or_create(
        empleado=empleado, fecha=fecha,
        defaults={
            'horario': horario,
            'entrada': entrada_time,
            'salida': salida_time,
            'comida_inicio': comida_inicio_time,
            'comida_fin': comida_fin_time,
            'horas_jornada': horas_jornada,
            'minutos_retardo': minutos_retardo,
            'minutos_extra': 0,
            'minutos_comida': minutos_comida,
            'incidencia_codigo': incidencia_final,
            'estatus': estatus,
        }
    )

    if incidencia_final:
        tipo = TipoIncidencia.objects.filter(codigo=incidencia_final).first()
        if tipo:
            RegistroIncidencia.objects.update_or_create(
                empleado=empleado,
                tipo=tipo,
                fecha=fecha,
                defaults={
                    'minutos': minutos_retardo if incidencia_final == RETARDO_CODIGO else minutos_comida,
                    'descripcion': f'Automático: {minutos_retardo} min de retardo' if incidencia_final == RETARDO_CODIGO
                                  else f'Excedió comida: {minutos_comida} min',
                }
            )

    return asistencia


def recalcular_todos_pendientes(fecha=None):
    """Recalcula todas las asistencias pendientes para una fecha.
    Útil para ejecutar al final del día.
    """
    from apps.empleados.models import Empleado

    if fecha is None:
        fecha = timezone.now().date()

    empleados = Empleado.objects.filter(estatus='activo')
    recalcular = 0
    for emp in empleados:
        try:
            asist = recalcular_asistencia(emp, fecha)
            if asist:
                recalcular += 1
        except Exception as e:
            logger.error(f'Error recalculando {emp.id_original} {fecha}: {e}')

    logger.info(f'Recalculados {recalcular} empleados para {fecha}')
    return recalcular
