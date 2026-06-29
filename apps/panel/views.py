from datetime import timedelta, date
from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Count, Q
from apps.empleados.models import Empleado
from apps.asistencia.models import Marcacion, AsistenciaDiaria
from apps.incidencias.models import RegistroIncidencia
from apps.registro.models import ConexionWeb


@login_required
def dashboard(request):
    # Empleados normales → dashboard simple
    if request.user.rol == 'normal':
        return render(request, 'panel/empleado.html')

    hoy = timezone.localtime().date()
    empleados_activos = Empleado.objects.filter(estatus='activo').count()
    empleados_renuncia = Empleado.objects.filter(estatus='renuncia').count()
    registros_hoy = Marcacion.objects.filter(marcado_en__date=hoy).count()

    return render(request, 'panel/index.html', {
        'hoy': hoy,
        'empleados_activos': empleados_activos,
        'empleados_renuncia': empleados_renuncia,
        'registros_hoy': registros_hoy,
    })


@login_required
def api_stats(request):
    hoy = timezone.localtime().date()
    inicio_mes = hoy.replace(day=1)

    empleados_activos = Empleado.objects.filter(estatus='activo').count()
    empleados_renuncia = Empleado.objects.filter(estatus='renuncia').count()

    registros_hoy = Marcacion.objects.filter(marcado_en__date=hoy).count()
    asistencias_hoy = AsistenciaDiaria.objects.filter(fecha=hoy)
    retardos_hoy = asistencias_hoy.filter(incidencia_codigo='llt').count()
    ausentes_hoy = asistencias_hoy.filter(estatus='ausente').count()
    completos_hoy = asistencias_hoy.filter(estatus='completo').count()

    hace_5min = timezone.now() - timedelta(minutes=5)
    conexiones_web = ConexionWeb.objects.filter(
        activa=True, ultimo_ping__gte=hace_5min
    ).count()

    incidencias_mes = RegistroIncidencia.objects.filter(
        fecha__gte=inicio_mes, fecha__lte=hoy
    ).count()
    incidencias_no_justificadas = RegistroIncidencia.objects.filter(
        fecha__gte=inicio_mes, fecha__lte=hoy, justificada=False
    ).count()

    # Gráfica: asistencias por día del mes
    asistencias_mes = AsistenciaDiaria.objects.filter(
        fecha__gte=inicio_mes, fecha__lte=hoy
    ).values('fecha').annotate(
        total=Count('id'),
        completos=Count('id', filter=Q(estatus='completo')),
        retardos=Count('id', filter=Q(incidencia_codigo='llt')),
        ausentes=Count('id', filter=Q(estatus='ausente')),
    ).order_by('fecha')

    return JsonResponse({
        'empleados_activos': empleados_activos,
        'empleados_renuncia': empleados_renuncia,
        'registros_hoy': registros_hoy,
        'retardos_hoy': retardos_hoy,
        'ausentes_hoy': ausentes_hoy,
        'completos_hoy': completos_hoy,
        'conexiones_web': conexiones_web,
        'incidencias_mes': incidencias_mes,
        'incidencias_no_justificadas': incidencias_no_justificadas,
        'asistencias_mes': [
            {
                'fecha': a['fecha'].isoformat(),
                'total': a['total'],
                'completos': a['completos'],
                'retardos': a['retardos'],
                'ausentes': a['ausentes'],
            }
            for a in asistencias_mes
        ],
    })
