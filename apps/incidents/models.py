from django.db import models
from django.conf import settings


class TipoIncidencia(models.Model):
    codigo = models.CharField('Código', max_length=20, unique=True)
    nombre = models.CharField('Nombre', max_length=100)
    descripcion = models.TextField('Descripción', blank=True, default='')
    color = models.CharField('Color (hex)', max_length=7, default='#FF0000',
                             help_text='Color en formato #RRGGBB')
    icono = models.CharField('Icono', max_length=50, blank=True, default='',
                             help_text='Clase de icono de Bootstrap')

    es_automatica = models.BooleanField('Es automática', default=False,
        help_text='Si es detectada automáticamente por el sistema (llt, finj)')
    requiere_justificacion = models.BooleanField('Requiere justificación', default=True)

    orden = models.PositiveIntegerField('Orden', default=0)

    class Meta:
        verbose_name = 'Tipo de incidencia'
        verbose_name_plural = 'Tipos de incidencia'
        db_table = 'tipos_incidencia'
        ordering = ['orden', 'codigo']

    def __str__(self):
        return f'[{self.codigo}] {self.nombre}'


class RegistroIncidencia(models.Model):
    empleado = models.ForeignKey(
        'employees.Empleado', on_delete=models.CASCADE,
        related_name='incidencias', verbose_name='Empleado'
    )
    tipo = models.ForeignKey(
        TipoIncidencia, on_delete=models.CASCADE,
        related_name='registros', verbose_name='Tipo'
    )
    fecha = models.DateField('Fecha')
    minutos = models.IntegerField('Minutos', default=0,
        help_text='Duración en minutos (aplica para retardos)')
    descripcion = models.TextField('Descripción', blank=True, default='')

    justificada = models.BooleanField('Justificada', default=False)
    justificacion = models.TextField('Justificación', blank=True, default='')
    atendida_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, verbose_name='Atendida por'
    )

    creado_en = models.DateTimeField('Creado en', auto_now_add=True)
    actualizado_en = models.DateTimeField('Actualizado en', auto_now=True)

    class Meta:
        verbose_name = 'Registro de incidencia'
        verbose_name_plural = 'Registros de incidencias'
        db_table = 'registros_incidencia'
        ordering = ['-fecha', '-creado_en']
        indexes = [
            models.Index(fields=['empleado', 'fecha']),
            models.Index(fields=['justificada']),
        ]

    def __str__(self):
        return f'{self.empleado.id_original} - [{self.tipo.codigo}] {self.fecha}'
