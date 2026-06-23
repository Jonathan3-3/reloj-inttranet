from django.db import models
from django.conf import settings


class Marcacion(models.Model):
    FUENTES = [
        ('scanner', 'Scanner ZKTeco'),
        ('web', 'Check-in Web'),
        ('manual', 'Manual'),
    ]
    TIPOS = [
        ('entrada', 'Entrada'),
        ('salida', 'Salida'),
        ('comida_inicio', 'Comida inicio'),
        ('comida_fin', 'Comida fin'),
        ('extra_inicio', 'Extra inicio'),
        ('extra_fin', 'Extra fin'),
    ]

    empleado = models.ForeignKey(
        'employees.Empleado', on_delete=models.CASCADE,
        related_name='marcaciones', verbose_name='Empleado'
    )
    marcado_en = models.DateTimeField('Marcado en')
    tipo = models.CharField('Tipo', max_length=20, choices=TIPOS, blank=True, default='')
    fuente = models.CharField('Fuente', max_length=20, choices=FUENTES, default='scanner')

    dispositivo_serial = models.CharField('Serial del dispositivo', max_length=50, blank=True, default='')
    ubicacion_lat = models.DecimalField('Latitud', max_digits=9, decimal_places=6, null=True, blank=True)
    ubicacion_lng = models.DecimalField('Longitud', max_digits=9, decimal_places=6, null=True, blank=True)
    ip_address = models.GenericIPAddressField('Dirección IP', blank=True, null=True)
    user_agent = models.TextField('User-Agent', blank=True, default='')

    datos_originales = models.TextField('Datos originales', blank=True, default='')
    creado_en = models.DateTimeField('Creado en', auto_now_add=True)

    class Meta:
        verbose_name = 'Marcación'
        verbose_name_plural = 'Marcaciones'
        db_table = 'marcaciones'
        ordering = ['-marcado_en']
        constraints = [
            models.UniqueConstraint(
                fields=['empleado', 'marcado_en'],
                name='unq_marcacion_empleado_fecha'
            )
        ]
        indexes = [
            models.Index(fields=['empleado', 'marcado_en']),
            models.Index(fields=['marcado_en']),
            models.Index(fields=['fuente']),
        ]

    def __str__(self):
        return f'{self.empleado.id_original} - {self.marcado_en}'


class AsistenciaDiaria(models.Model):
    ESTADOS = [
        ('completo', 'Completo'),
        ('pendiente', 'Pendiente'),
        ('ausente', 'Ausente'),
        ('descanso', 'Descanso'),
    ]

    empleado = models.ForeignKey(
        'employees.Empleado', on_delete=models.CASCADE,
        related_name='asistencias', verbose_name='Empleado'
    )
    fecha = models.DateField('Fecha')
    horario = models.ForeignKey(
        'schedules.Horario', on_delete=models.SET_NULL,
        null=True, blank=True, verbose_name='Horario aplicado'
    )

    entrada = models.TimeField('Entrada', null=True, blank=True)
    salida = models.TimeField('Salida', null=True, blank=True)
    comida_inicio = models.TimeField('Comida inicio', null=True, blank=True)
    comida_fin = models.TimeField('Comida fin', null=True, blank=True)

    horas_jornada = models.DecimalField('Horas jornada', max_digits=5, decimal_places=2, default=0)
    minutos_retardo = models.IntegerField('Minutos de retardo', default=0)
    minutos_extra = models.IntegerField('Minutos extra', default=0)
    minutos_comida = models.IntegerField('Minutos de comida', default=0)

    incidencia_codigo = models.CharField('Código de incidencia', max_length=20, blank=True, default='')
    estatus = models.CharField('Estatus', max_length=20, choices=ESTADOS, default='pendiente')

    calculado_en = models.DateTimeField('Calculado en', auto_now=True)

    class Meta:
        verbose_name = 'Asistencia diaria'
        verbose_name_plural = 'Asistencias diarias'
        db_table = 'asistencias_diarias'
        unique_together = ['empleado', 'fecha']
        indexes = [
            models.Index(fields=['empleado', 'fecha']),
            models.Index(fields=['fecha', 'estatus']),
        ]

    def __str__(self):
        return f'{self.empleado.id_original} - {self.fecha} ({self.estatus})'
