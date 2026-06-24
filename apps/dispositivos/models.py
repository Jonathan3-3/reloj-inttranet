from django.db import models


class Dispositivo(models.Model):
    TIPOS = [
        ('scanner', 'Scanner ZKTeco'),
        ('web', 'Navegador Web'),
    ]
    ESTADOS = [
        ('online', 'En línea'),
        ('offline', 'Fuera de línea'),
        ('mantenimiento', 'En mantenimiento'),
    ]

    serial = models.CharField('Serial', max_length=50, unique=True)
    nombre = models.CharField('Nombre', max_length=100)
    ip = models.GenericIPAddressField('Dirección IP', blank=True, null=True)
    puerto = models.IntegerField('Puerto', default=4370)
    modelo = models.CharField('Modelo', max_length=100, default='SpeedFace-V3L')
    tipo = models.CharField('Tipo', max_length=20, choices=TIPOS, default='scanner')
    estado = models.CharField('Estado', max_length=20, choices=ESTADOS, default='offline')
    password = models.CharField('Password', max_length=50, blank=True, default='0',
                                help_text='Password de comunicación del dispositivo')

    ultimo_ping = models.DateTimeField('Último ping', null=True, blank=True)
    ultima_sincronizacion = models.DateTimeField('Última sincronización', null=True, blank=True)
    activo = models.BooleanField('Activo', default=True)

    creado_en = models.DateTimeField('Creado en', auto_now_add=True)
    actualizado_en = models.DateTimeField('Actualizado en', auto_now=True)

    class Meta:
        verbose_name = 'Dispositivo'
        verbose_name_plural = 'Dispositivos'
        db_table = 'dispositivos'
        ordering = ['nombre']

    def __str__(self):
        return f'{self.nombre} ({self.serial})'
