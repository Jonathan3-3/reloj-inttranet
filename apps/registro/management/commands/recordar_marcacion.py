from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.empleados.models import Empleado
from apps.asistencia.models import Marcacion
from apps.solicitudes.models import PushToken, enviar_push_expo


class Command(BaseCommand):
    help = 'Envía push a empleados sin entrada hoy'

    def handle(self, *args, **options):
        hoy = timezone.localtime().date()
        ahora = timezone.now()
        hora_limite = ahora.replace(hour=9, minute=0, second=0)

        if ahora < hora_limite:
            self.stdout.write('Todavía no son las 9:00 AM')
            return

        empleados_sin_entrada = Empleado.objects.filter(
            estatus='activo',
        ).exclude(
            id__in=Marcacion.objects.filter(
                marcado_en__date=hoy,
                accion='entrada',
            ).values('empleado_id'),
        )

        enviados = 0
        for emp in empleados_sin_entrada:
            if PushToken.objects.filter(empleado=emp, activo=True).exists():
                enviar_push_expo(
                    emp,
                    'PunchTrack',
                    '¡Recuerda hacer tus marcaciones por favor ⏰',
                    datos={'screen': 'Checkin'},
                )
                enviados += 1

        self.stdout.write(f'Recordatorio enviado a {enviados} empleados')
