import os
os.environ["DJANGO_SECRET_KEY"] = "test"
os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings.local"
import django
django.setup()
from apps.asistencia.models import Marcacion
from django.utils import timezone

total = Marcacion.objects.filter(fuente="scanner").count()
print(f"Total scanner: {total}")
marcas = Marcacion.objects.filter(fuente="scanner").order_by("-marcado_en")[:15]
for m in marcas:
    local = timezone.localtime(m.marcado_en)
    print(f"#{m.id} Emp={m.empleado_id} UTC={m.marcado_en.strftime('%H:%M:%S')} LOCAL={local.strftime('%H:%M:%S')} Fecha={local.strftime('%Y-%m-%d')}")
