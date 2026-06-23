"""Módulo de comunicación con dispositivos ZKTeco vía pyzk."""
import logging
from datetime import datetime, timedelta
from django.utils import timezone
from django.db import transaction

logger = logging.getLogger(__name__)


def sincronizar_dispositivo(dispositivo):
    """Sincroniza empleados y asistencia desde un dispositivo ZKTeco."""
    if dispositivo.tipo != 'scanner':
        raise ValueError(f'El dispositivo {dispositivo.nombre} no es un scanner')

    try:
        from zk import ZK, const
        zk = ZK(
            str(dispositivo.ip),
            port=dispositivo.puerto,
            timeout=30,
            password=int(dispositivo.password or 0),
        )
        conn = zk.connect()
        logger.info(f'Conectado a {dispositivo.nombre} ({dispositivo.ip})')
    except Exception as e:
        logger.error(f'Error conectando a {dispositivo.nombre}: {e}')
        raise

    resultado = {'empleados': 0, 'marcaciones': 0, 'errores': 0}

    try:
        # Sincronizar empleados
        from apps.employees.models import Empleado
        usuarios = conn.get_users()
        nuevos = 0
        for u in usuarios:
            try:
                user_id = str(u.user_id)
                nombre = u.name or f'Empleado {user_id}'
                Empleado.objects.get_or_create(
                    id_original=user_id,
                    defaults={'nombre': nombre, 'id_en_dispositivo': user_id}
                )
                nuevos += 1
            except Exception as e:
                logger.warning(f'Error con usuario {u.user_id}: {e}')
                resultado['errores'] += 1
        resultado['empleados'] = nuevos

        # Sincronizar marcaciones
        from apps.attendance.models import Marcacion
        from apps.attendance.calculators.engine import recalcular_asistencia

        marcas = conn.get_attendance()
        for m in marcas:
            try:
                user_id = str(m.user_id)
                timestamp = m.timestamp
                if isinstance(timestamp, str):
                    timestamp = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
                if timezone.is_naive(timestamp):
                    timestamp = timezone.make_aware(timestamp)

                empleado = Empleado.objects.filter(
                    Q(id_original=user_id) | Q(id_en_dispositivo=user_id)
                ).first()
                if not empleado:
                    continue

                _, created = Marcacion.objects.get_or_create(
                    empleado=empleado,
                    marcado_en=timestamp,
                    defaults={
                        'fuente': 'scanner',
                        'dispositivo_serial': dispositivo.serial,
                        'datos_originales': str(m),
                    }
                )
                if created:
                    resultado['marcaciones'] += 1
                    recalcular_asistencia(empleado, timestamp.date())
            except Exception as e:
                logger.warning(f'Error procesando marcación: {e}')
                resultado['errores'] += 1

        dispositivo.ultima_sincronizacion = timezone.now()
        dispositivo.estado = 'online'
        dispositivo.save()

    finally:
        try:
            conn.disconnect()
        except Exception:
            pass

    logger.info(f'Sincronización completada: {resultado}')
    return resultado
