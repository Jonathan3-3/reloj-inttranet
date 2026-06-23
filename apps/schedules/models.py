from django.db import models


class Horario(models.Model):
    TIPO_ASIGNACION = [
        ('departamento', 'Departamento'),
        ('area', 'Area'),
        ('individual', 'Individual'),
    ]

    nombre = models.CharField('Nombre del horario', max_length=100)

    ventana_entrada_inicio = models.TimeField('Inicio ventana de entrada')
    ventana_entrada_fin = models.TimeField('Fin ventana de entrada')
    prorroga_minutos = models.PositiveIntegerField('Prórroga (minutos)', default=10,
        help_text='Minutos de tolerancia después del inicio de la ventana')
    tolerancia_ausencia_minutos = models.PositiveIntegerField(
        'Tolerancia para ausencia (minutos)', default=60,
        help_text='Si no marca en este tiempo después del inicio, se considera ausente'
    )

    comida_ventana_inicio = models.TimeField('Inicio ventana de comida')
    comida_ventana_fin = models.TimeField('Fin ventana de comida')
    comida_duracion_minutos = models.PositiveIntegerField(
        'Duración de comida permitida (minutos)', default=60
    )

    jornada_hrs = models.DecimalField('Horas de jornada', max_digits=4, decimal_places=2, default=8.00)

    tipo_asignacion = models.CharField('Tipo de asignación', max_length=20, choices=TIPO_ASIGNACION)
    activo = models.BooleanField('Activo', default=True)

    areas = models.ManyToManyField('company.Area', blank=True, verbose_name='Areas')
    departamentos = models.ManyToManyField('company.Departamento', blank=True, verbose_name='Departamentos')
    empleados = models.ManyToManyField(
        'employees.Empleado', blank=True, verbose_name='Empleados',
        help_text='Solo para asignación individual'
    )

    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Horario'
        verbose_name_plural = 'Horarios'
        db_table = 'horarios'
        ordering = ['nombre']

    def __str__(self):
        return f'{self.nombre} ({self.ventana_entrada_inicio}-{self.ventana_entrada_fin})'


class AsignacionHorario(models.Model):
    empleado = models.ForeignKey(
        'employees.Empleado', on_delete=models.CASCADE,
        related_name='asignaciones_horario', verbose_name='Empleado'
    )
    horario = models.ForeignKey(
        Horario, on_delete=models.CASCADE,
        related_name='asignaciones', verbose_name='Horario'
    )
    fecha_inicio = models.DateField('Fecha de inicio')
    fecha_fin = models.DateField('Fecha de fin', null=True, blank=True)

    class Meta:
        verbose_name = 'Asignación de horario'
        verbose_name_plural = 'Asignaciones de horario'
        db_table = 'asignaciones_horario'
        ordering = ['-fecha_inicio']
        indexes = [
            models.Index(fields=['empleado', 'fecha_inicio']),
        ]

    def __str__(self):
        fin = self.fecha_fin or 'Actual'
        return f'{self.empleado} -> {self.horario} ({self.fecha_inicio} a {fin})'


class ExcepcionHorario(models.Model):
    empleado = models.ForeignKey(
        'employees.Empleado', on_delete=models.CASCADE,
        related_name='excepciones_horario', verbose_name='Empleado'
    )
    fecha = models.DateField('Fecha')
    entrada_esperada = models.TimeField('Entrada esperada', null=True, blank=True)
    salida_esperada = models.TimeField('Salida esperada', null=True, blank=True)
    motivo = models.CharField('Motivo', max_length=200)

    class Meta:
        verbose_name = 'Excepción de horario'
        verbose_name_plural = 'Excepciones de horario'
        db_table = 'excepciones_horario'
        unique_together = ['empleado', 'fecha']

    def __str__(self):
        return f'{self.empleado} - {self.fecha}: {self.motivo}'
