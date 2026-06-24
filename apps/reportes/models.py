from django.db import models
from django.conf import settings


class PlantillaReporte(models.Model):
    TIPOS = [
        ('diario', 'Reporte diario'),
        ('mensual', 'Reporte mensual'),
        ('retardos', 'Reporte de retardos'),
        ('incidencias', 'Reporte de incidencias'),
        ('personalizado', 'Personalizado'),
    ]
    FORMATOS = [
        ('xlsx', 'Excel (XLSX)'),
        ('pdf', 'PDF'),
        ('csv', 'CSV'),
    ]

    nombre = models.CharField('Nombre', max_length=100)
    tipo = models.CharField('Tipo', max_length=20, choices=TIPOS)
    formato = models.CharField('Formato', max_length=10, choices=FORMATOS, default='xlsx')

    mostrar_columnas = models.JSONField('Columnas a mostrar', default=list, blank=True,
        help_text='Lista de nombres de columna a incluir')

    creado_en = models.DateTimeField('Creado en', auto_now_add=True)
    actualizado_en = models.DateTimeField('Actualizado en', auto_now=True)

    class Meta:
        verbose_name = 'Plantilla de reporte'
        verbose_name_plural = 'Plantillas de reporte'
        db_table = 'plantillas_reporte'

    def __str__(self):
        return f'{self.nombre} ({self.get_tipo_display()})'


class ReporteGenerado(models.Model):
    plantilla = models.ForeignKey(
        PlantillaReporte, on_delete=models.CASCADE,
        related_name='reportes', verbose_name='Plantilla'
    )
    generado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, verbose_name='Generado por'
    )
    archivo = models.FileField('Archivo', upload_to='reportes/', max_length=255)
    fecha_inicio = models.DateField('Fecha inicio')
    fecha_fin = models.DateField('Fecha fin')
    descargado = models.BooleanField('Descargado', default=False)
    creado_en = models.DateTimeField('Creado en', auto_now_add=True)

    class Meta:
        verbose_name = 'Reporte generado'
        verbose_name_plural = 'Reportes generados'
        db_table = 'reportes_generados'
        ordering = ['-creado_en']

    def __str__(self):
        return f'{self.plantilla.nombre} ({self.fecha_inicio} - {self.fecha_fin})'
