import os
os.environ["DJANGO_SECRET_KEY"] = "test"
os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings.local"
import django
django.setup()
from apps.dispositivos.models import Dispositivo

for d in Dispositivo.objects.all():
    print(f"#{d.id} serial={d.serial} ip={d.ip} activo={d.activo} estado={d.estado}")
print(f"Total dispositivos: {Dispositivo.objects.count()}")
