"""Módulo de comunicación con dispositivos ZKTeco."""
import logging
from datetime import datetime
from django.utils import timezone
from django.db import transaction
from django.db.models import Q

logger = logging.getLogger(__name__)


def sincronizar_dispositivo(dispositivo):
    """Sincroniza empleados y asistencia desde un dispositivo ZKTeco.
    Primero intenta vía pyzk (puerto 4370), si falla indica configuración manual.
    """
    if dispositivo.tipo != 'scanner':
        raise ValueError(f'El dispositivo {dispositivo.nombre} no es un scanner')

    resultado = {'empleados': 0, 'marcaciones': 0, 'errores': 0, 'metodo': 'none'}

    # Intentar pyzk
    try:
        from zk import ZK
        zk = ZK(
            str(dispositivo.ip),
            port=dispositivo.puerto or 4370,
            timeout=30,
            password=int(dispositivo.password or 0),
        )
        conn = zk.connect()
        logger.info(f'ZK conectado a {dispositivo.nombre} ({dispositivo.ip})')
    except Exception as e:
        logger.warning(f'ZK no disponible para {dispositivo.nombre}: {e}')
        logger.warning(
            f'El scanner {dispositivo.nombre} ({dispositivo.ip}) no responde en puerto ZK. '
            f'Configure PUSH manual desde la web del scanner: http://{dispositivo.ip}/'
        )
        raise ConnectionError(
            f'Scanner {dispositivo.nombre} no conecta vía ZK (puerto {dispositivo.puerto or 4370} cerrado). '
            f'Configure PUSH desde el navegador en http://{dispositivo.ip}/ '
            f'o verifique que el puerto esté abierto.'
        )

    try:
        from apps.empleados.models import Empleado
        from apps.asistencia.models import Marcacion
        from apps.asistencia.calculators.engine import recalcular_asistencia

        usuarios = conn.get_users()
        for u in usuarios:
            try:
                user_id = str(u.user_id)
                nombre = u.name or f'Empleado {user_id}'
                Empleado.objects.get_or_create(
                    id_original=user_id,
                    defaults={'nombre': nombre, 'id_en_dispositivo': user_id}
                )
                resultado['empleados'] += 1
            except Exception as e:
                logger.warning(f'Error con usuario {u.user_id}: {e}')
                resultado['errores'] += 1

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
