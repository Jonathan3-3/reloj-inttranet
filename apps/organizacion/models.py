from django.db import models

class Area(models.Model):
    nombre = models.CharField('Nombre', max_length=100, unique=True)
    responsable = models.ForeignKey(
        'empleados.Empleado', on_delete=models.SET_NULL,
        null=True, blank=True, verbose_name='Responsable',
        related_name='area_responsable'
    )

    class Meta:
        verbose_name = 'Area'
        verbose_name_plural = 'Areas'
        db_table = 'areas'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class Departamento(models.Model):
    nombre = models.CharField('Nombre', max_length=100)
    area = models.ForeignKey(
        Area, on_delete=models.CASCADE,
        related_name='departamentos', verbose_name='Area'
    )

    class Meta:
        verbose_name = 'Departamento'
        verbose_name_plural = 'Departamentos'
        db_table = 'departamentos'
        ordering = ['nombre']
        unique_together = ['nombre', 'area']

    def __str__(self):
        return f'{self.nombre} ({self.area.nombre})'
