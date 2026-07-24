from datetime import timedelta, date
from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.utils import timezone
from django.db.models import Count, Q
from apps.empleados.models import Empleado
from apps.asistencia.models import Marcacion, AsistenciaDiaria
from apps.incidencias.models import RegistroIncidencia
from apps.registro.models import ConexionWeb
from apps.solicitudes.models import Solicitud
from apps.dispositivos.models import Dispositivo
from apps.movil.models import VersionAPK


@login_required
def dashboard(request):
    # Empleados normales → dashboard simple
    if request.user.rol == 'normal':
        return render(request, 'panel/empleado.html')

    hoy = timezone.localtime().date()
    empleados_activos = Empleado.objects.filter(estatus='activo').count()
    empleados_renuncia = Empleado.objects.filter(estatus='renuncia').count()
    registros_hoy = Marcacion.objects.filter(marcado_en__date=hoy).count()
    solicitudes_recientes = Solicitud.objects.select_related('empleado')[:8]

    dispositivos = Dispositivo.objects.filter(tipo='scanner').order_by('nombre')
    apk_activa = VersionAPK.objects.filter(activa=True).first()

    return render(request, 'panel/index.html', {
        'hoy': hoy,
        'empleados_activos': empleados_activos,
        'empleados_renuncia': empleados_renuncia,
        'registros_hoy': registros_hoy,
        'solicitudes_recientes': solicitudes_recientes,
        'dispositivos': dispositivos,
        'apk_activa': apk_activa,
    })


@login_required
@staff_member_required
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

    solicitudes_recientes = Solicitud.objects.select_related('empleado').order_by('-creado_en')[:8]

    # Gráfica: asistencias por día del mes
    asistencias_mes = AsistenciaDiaria.objects.filter(
        fecha__gte=inicio_mes, fecha__lte=hoy
    ).values('fecha').annotate(
        total=Count('id'),
        completos=Count('id', filter=Q(estatus='completo')),
        retardos=Count('id', filter=Q(incidencia_codigo='llt')),
        ausentes=Count('id', filter=Q(estatus='ausente')),
    ).order_by('fecha')

    solicitudes_json = [
        {
            'id': s.id,
            'empleado_nombre': s.empleado.nombre_completo,
            'empleado_id': s.empleado.id_original,
            'tipo': s.get_tipo_display(),
            'estatus': s.get_estatus_display(),
            'estatus_codigo': s.estatus,
            'fecha_inicio': s.fecha_inicio.isoformat(),
            'fecha_fin': s.fecha_fin.isoformat(),
            'creado_en': s.creado_en.isoformat(),
        }
        for s in solicitudes_recientes
    ]

    dispositivos = Dispositivo.objects.filter(tipo='scanner').order_by('nombre')
    ahora = timezone.now()
    hace_5min_dt = ahora - timedelta(minutes=5)

    dispositivos_json = []
    for d in dispositivos:
        online = d.ultimo_heartbeat and d.ultimo_heartbeat >= hace_5min_dt
        dispositivos_json.append({
            'id': d.id,
            'serial': d.serial,
            'nombre': d.nombre,
            'ip': d.ip or '',
            'modelo': d.modelo,
            'estado': 'online' if online else 'offline',
            'ultimo_heartbeat': d.ultimo_heartbeat.isoformat() if d.ultimo_heartbeat else None,
            'ultimo_attlog': d.ultimo_attlog.isoformat() if d.ultimo_attlog else None,
            'ultimo_error': d.ultimo_error or '',
        })

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
        'solicitudes_recientes': solicitudes_json,
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
        'dispositivos': dispositivos_json,
    })
