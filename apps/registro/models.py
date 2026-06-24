from django.db import models


class ConexionWeb(models.Model):
    empleado = models.ForeignKey(
        'empleados.Empleado', on_delete=models.CASCADE,
        related_name='conexiones', verbose_name='Empleado'
    )
    session_id = models.CharField('ID de sesión', max_length=100, unique=True)
    ip_address = models.GenericIPAddressField('Dirección IP')
    user_agent = models.TextField('User-Agent', blank=True, default='')
    tipo_dispositivo = models.CharField('Tipo de dispositivo', max_length=10, blank=True, default='',
        help_text='movil o pc')
    navegador = models.CharField('Navegador', max_length=50, blank=True, default='')

    ubicacion_lat = models.DecimalField('Latitud', max_digits=9, decimal_places=6, null=True, blank=True)
    ubicacion_lng = models.DecimalField('Longitud', max_digits=9, decimal_places=6, null=True, blank=True)

    conectado_desde = models.DateTimeField('Conectado desde', auto_now_add=True)
    ultimo_ping = models.DateTimeField('Último ping', auto_now=True)
    activa = models.BooleanField('Activa', default=True)

    class Meta:
        verbose_name = 'Conexión web'
        verbose_name_plural = 'Conexiones web'
        db_table = 'conexiones_web'
        ordering = ['-ultimo_ping']
        indexes = [
            models.Index(fields=['activa']),
            models.Index(fields=['empleado', 'activa']),
        ]

    def __str__(self):
        dev = self.tipo_dispositivo or 'desconocido'
        return f'{self.empleado.id_original} - {dev} ({self.ip_address})'

    @property
    def tiempo_conectado(self):
        from django.utils import timezone
        delta = timezone.now() - self.conectado_desde
        horas = delta.total_seconds() // 3600
        minutos = (delta.total_seconds() % 3600) // 60
        if horas > 0:
            return f'{int(horas)}h {int(minutos)}m'
        return f'{int(minutos)}m'
