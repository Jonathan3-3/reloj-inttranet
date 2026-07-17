import os
os.environ['DJANGO_SECRET_KEY'] = 'test'
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings.local'
import django
django.setup()

from datetime import datetime, date
from django.utils import timezone

from apps.asistencia.calculators.engine import recalcular_asistencia, clasificar_punches
from apps.empleados.models import Empleado
from apps.asistencia.models import Marcacion, AsistenciaDiaria

e = Empleado.objects.filter(id_original='13').first()
print(f'Empleado: {e.nombre_completo} (depto: {e.departamento})')

ahora = timezone.now()
m = Marcacion.objects.create(empleado=e, marcado_en=ahora, fuente='web')
print(f'Marcacion creada: UTC={ahora.time()} / CST={timezone.localtime(ahora).time()}')

asis = recalcular_asistencia(e, ahora.date())
if asis:
    print(f'Estatus: {asis.estatus}')
    print(f'Entrada: {asis.entrada}')
    print(f'Minutos retardo: {asis.minutos_retardo}')
    print(f'Incidencia: {asis.incidencia_codigo}')
else:
    print('Sin horario asignado - recalculo omitido')
    print('Esto es normal, ningun empleado tiene horario asignado aun.')
