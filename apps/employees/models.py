from django.db import models
from django.conf import settings


class Cargo(models.Model):
    nombre = models.CharField('Nombre', max_length=100, unique=True)

    class Meta:
        verbose_name = 'Cargo'
        verbose_name_plural = 'Cargos'
        db_table = 'cargos'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class Empleado(models.Model):
    ESTATUS = [
        ('activo', 'Activo'),
        ('inactivo', 'Inactivo'),
        ('renuncia', 'Renuncia'),
    ]
    TIPO_EMPLEADO = [
        ('empleado', 'Empleado'),
        ('admin', 'Administrador'),
        ('superadmin', 'Super Administrador'),
    ]
    TIPO_VERIFICACION = [
        ('huella', 'Huella'),
        ('facial', 'Facial'),
        ('ambos', 'Huella y Facial'),
    ]
    GENERO = [
        ('masculino', 'Masculino'),
        ('femenino', 'Femenino'),
        ('otro', 'Otro'),
    ]

    id_original = models.CharField('ID original', max_length=20, unique=True,
                                   help_text='Código del empleado ej: AER015')
    nombre = models.CharField('Nombre(s)', max_length=100)
    apellidos = models.CharField('Apellidos', max_length=200, default='')
    departamento = models.ForeignKey(
        'company.Departamento', on_delete=models.SET_NULL,
        null=True, blank=True, verbose_name='Departamento'
    )
    cargo = models.ForeignKey(
        Cargo, on_delete=models.SET_NULL,
        null=True, blank=True, verbose_name='Cargo'
    )
    tipo_empleado = models.CharField('Tipo de empleado', max_length=20, choices=TIPO_EMPLEADO, default='empleado')
    telefono = models.CharField('Teléfono', max_length=20, blank=True, default='')
    email = models.EmailField('Correo electrónico', blank=True, default='')
    estatus = models.CharField('Estatus', max_length=20, choices=ESTATUS, default='activo')
    fecha_ingreso = models.DateField('Fecha de contratación', null=True, blank=True)
    fecha_renuncia = models.DateField('Fecha de renuncia', null=True, blank=True)
    fecha_recontratacion = models.DateField('Fecha de recontratación', null=True, blank=True)

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, verbose_name='Usuario del sistema'
    )

    # INFO PERSONAL
    nss = models.CharField('NSS', max_length=20, blank=True, default='')
    ciudad = models.CharField('Ciudad', max_length=100, blank=True, default='')
    cp = models.CharField('Código Postal', max_length=10, blank=True, default='')
    nacionalidad = models.CharField('Nacionalidad', max_length=100, blank=True, default='')
    genero = models.CharField('Género', max_length=20, choices=GENERO, blank=True, default='')

    # CONFIGURACIÓN SCANNER
    id_en_dispositivo = models.CharField('ID en scanner', max_length=50, blank=True, default='',
                                         help_text='ID del empleado dentro del dispositivo ZKTeco')
    tipo_verificacion_scanner = models.CharField(
        'Tipo verificación', max_length=20, choices=TIPO_VERIFICACION,
        default='facial', help_text='Huella, facial o ambos'
    )
    foto = models.ImageField('Foto', upload_to='fotos/', blank=True)

    creado_en = models.DateTimeField('Creado en', auto_now_add=True)
    actualizado_en = models.DateTimeField('Actualizado en', auto_now=True)

    class Meta:
        verbose_name = 'Empleado'
        verbose_name_plural = 'Empleados'
        db_table = 'empleados'
        ordering = ['nombre']
        indexes = [
            models.Index(fields=['estatus']),
            models.Index(fields=['departamento']),
        ]

    def __str__(self):
        return f'{self.id_original} - {self.nombre_completo}'

    @property
    def nombre_completo(self):
        return f'{self.nombre} {self.apellidos}'.strip()

    @property
    def id_visual(self):
        return self.id_original

    @property
    def id_numerico(self):
        import re
        match = re.search(r'(\d+)', self.id_original)
        return int(match.group(1)) if match else 0

    @property
    def es_activo(self):
        return self.estatus == 'activo'
