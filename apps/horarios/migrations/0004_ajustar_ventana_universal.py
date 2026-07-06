from datetime import time
from django.db import migrations


def ajustar_ventana(apps, schema_editor):
    Horario = apps.get_model('horarios', 'Horario')
    Horario.objects.filter(nombre='Universal').update(
        ventana_entrada_inicio=time(6, 0),
        ventana_entrada_fin=time(10, 0),
    )


class Migration(migrations.Migration):

    dependencies = [
        ('horarios', '0003_horario_clasificacion_secuencial_and_more'),
    ]

    operations = [
        migrations.RunPython(ajustar_ventana, migrations.RunPython.noop),
    ]
