from django.db import models
from django.conf import settings
from django.core.validators import FileExtensionValidator
from django.utils import timezone


class Solicitud(models.Model):
    TIPOS = [
        ('vacaciones', 'Vacaciones'),
        ('incapacidad', 'Incapacidad'),
        ('maternidad', 'Maternidad'),
        ('paternidad', 'Paternidad'),
        ('permiso_cgoce', 'Permiso con goce de sueldo'),
        ('permiso_sgoce', 'Permiso sin goce de sueldo'),
        ('salida_temprana', 'Salida temprana'),
        ('entrada_tarde', 'Entrada tarde'),
    ]
    ESTATUS = [
        ('pendiente', 'Pendiente'),
        ('aprobada', 'Aprobada'),
        ('rechazada', 'Rechazada'),
    ]

    empleado = models.ForeignKey(
        'empleados.Empleado', on_delete=models.CASCADE,
        related_name='solicitudes', verbose_name='Empleado'
    )
    tipo = models.CharField('Tipo de solicitud', max_length=20, choices=TIPOS)
    fecha_inicio = models.DateField('Fecha de inicio')
    fecha_fin = models.DateField('Fecha de fin')
    descripcion = models.TextField('Descripción', blank=True, default='')
    archivo = models.FileField(
        'Documento', upload_to='solicitudes/',
        blank=True, null=True,
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'jpg', 'jpeg', 'png'])],
        help_text='PDF o JPG (máx 5MB)'
    )

    estatus = models.CharField('Estatus', max_length=20, choices=ESTATUS, default='pendiente')
    aprobada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, verbose_name='Aprobada por'
    )
    fecha_aprobacion = models.DateTimeField('Fecha de aprobación', null=True, blank=True)
    comentario_admin = models.TextField('Comentario del admin', blank=True, default='')

    creado_en = models.DateTimeField('Creado en', auto_now_add=True)
    actualizado_en = models.DateTimeField('Actualizado en', auto_now=True)

    class Meta:
        verbose_name = 'Solicitud'
        verbose_name_plural = 'Solicitudes'
        db_table = 'solicitudes'
        ordering = ['-creado_en']
        indexes = [
            models.Index(fields=['estatus']),
            models.Index(fields=['empleado', 'estatus']),
        ]

    def __str__(self):
        return f'{self.empleado.id_original} - {self.get_tipo_display()} ({self.get_estatus_display()})'

    @property
    def dias_solicitados(self):
        return (self.fecha_fin - self.fecha_inicio).days + 1

    def aprobar(self, usuario):
        from apps.horarios.models import ExcepcionHorario
        from apps.incidencias.models import TipoIncidencia, RegistroIncidencia
        from apps.asistencia.calculators.engine import recalcular_asistencia

        self.estatus = 'aprobada'
        self.aprobada_por = usuario
        self.fecha_aprobacion = timezone.now()
        self.save()

        # Mapear tipo de solicitud a código de incidencia
        mapa = {
            'vacaciones': 'pcgs',
            'incapacidad': 'inc',
            'maternidad': 'mat',
            'paternidad': 'pat',
            'permiso_cgoce': 'pcgs',
            'permiso_sgoce': 'pcgs',
            'salida_temprana': 'sta',
            'entrada_tarde': 'sta',
        }
        cod_incidencia = mapa.get(self.tipo, 'pcgs')

        # Crear excepción de horario para cada día
        fecha_actual = self.fecha_inicio
        while fecha_actual <= self.fecha_fin:
            ExcepcionHorario.objects.get_or_create(
                empleado=self.empleado,
                fecha=fecha_actual,
                defaults={
                    'motivo': f'{self.get_tipo_display()} aprobado',
                }
            )
            # Registrar incidencia justificada
            try:
                tipo_inc = TipoIncidencia.objects.get(codigo=cod_incidencia)
                RegistroIncidencia.objects.get_or_create(
                    empleado=self.empleado,
                    tipo=tipo_inc,
                    fecha=fecha_actual,
                    defaults={
                        'minutos': 0,
                        'descripcion': f'{self.get_tipo_display()} - Aprobado por {usuario.get_full_name()}',
                        'justificada': True,
                        'justificacion': f'Aprobado automáticamente vía solicitud. Ref: {self.id}',
                        'atendida_por': usuario,
                    }
                )
            except TipoIncidencia.DoesNotExist:
                pass

            # Recalcular asistencia para esta fecha
            recalcular_asistencia(self.empleado, fecha_actual)

            fecha_actual += timezone.timedelta(days=1)

        # Crear notificación
        Notificacion.objects.create(
            empleado=self.empleado,
            tipo='solicitud_aprobada',
            titulo=f'Solicitud aprobada: {self.get_tipo_display()}',
            mensaje=f'Tu solicitud de {self.get_tipo_display()} del {self.fecha_inicio} al {self.fecha_fin} fue aprobada.',
        )
        enviar_push_expo(
            self.empleado,
            f'Solicitud aprobada: {self.get_tipo_display()}',
            f'Tu solicitud de {self.get_tipo_display()} del {self.fecha_inicio} al {self.fecha_fin} fue aprobada.',
        )

    def rechazar(self, usuario, comentario=''):
        self.estatus = 'rechazada'
        self.aprobada_por = usuario
        self.fecha_aprobacion = timezone.now()
        self.comentario_admin = comentario
        self.save()

        Notificacion.objects.create(
            empleado=self.empleado,
            tipo='solicitud_rechazada',
            titulo=f'Solicitud rechazada: {self.get_tipo_display()}',
            mensaje=f'Tu solicitud de {self.get_tipo_display()} fue rechazada. Motivo: {comentario or "Sin especificar"}',
        )
        enviar_push_expo(
            self.empleado,
            f'Solicitud rechazada: {self.get_tipo_display()}',
            f'Tu solicitud de {self.get_tipo_display()} fue rechazada. Motivo: {comentario or "Sin especificar"}',
        )


class Notificacion(models.Model):
    TIPOS = [
        ('solicitud_nueva', 'Nueva solicitud'),
        ('solicitud_aprobada', 'Solicitud aprobada'),
        ('solicitud_rechazada', 'Solicitud rechazada'),
        ('aviso', 'Aviso general'),
    ]

    empleado = models.ForeignKey(
        'empleados.Empleado', on_delete=models.CASCADE,
        null=True, blank=True, related_name='notificaciones',
        verbose_name='Empleado'
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        null=True, blank=True, related_name='notificaciones',
        verbose_name='Usuario'
    )
    tipo = models.CharField('Tipo', max_length=30, choices=TIPOS)
    titulo = models.CharField('Título', max_length=200)
    mensaje = models.TextField('Mensaje', blank=True, default='')
    url = models.CharField('URL', max_length=300, blank=True, default='')
    leida = models.BooleanField('Leída', default=False)
    creado_en = models.DateTimeField('Creado en', auto_now_add=True)

    class Meta:
        verbose_name = 'Notificación'
        verbose_name_plural = 'Notificaciones'
        db_table = 'notificaciones'
        ordering = ['-creado_en']

    def __str__(self):
        return self.titulo


class PushToken(models.Model):
    empleado = models.ForeignKey(
        'empleados.Empleado', on_delete=models.CASCADE,
        related_name='push_tokens', verbose_name='Empleado'
    )
    token = models.CharField('Token Expo Push', max_length=255, unique=True)
    activo = models.BooleanField('Activo', default=True)
    creado_en = models.DateTimeField('Creado en', auto_now_add=True)
    actualizado_en = models.DateTimeField('Actualizado en', auto_now=True)

    class Meta:
        verbose_name = 'Push Token'
        verbose_name_plural = 'Push Tokens'
        db_table = 'push_tokens'

    def __str__(self):
        return f'{self.empleado.id_original} - {self.token[:20]}...'


def enviar_push_expo(empleado, titulo, cuerpo, datos=None):
    import json
    from urllib.request import Request, urlopen
    from urllib.error import URLError

    tokens = PushToken.objects.filter(empleado=empleado, activo=True).values_list('token', flat=True)
    if not tokens:
        return

    mensajes = [
        {
            'to': t,
            'title': titulo,
            'body': cuerpo,
            'sound': 'default',
            'priority': 'high',
            **(datos or {}),
        }
        for t in tokens
    ]

    req = Request(
        'https://exp.host/--/api/v2/push/send',
        data=json.dumps(mensajes).encode('utf-8'),
        headers={'Content-Type': 'application/json'},
        method='POST',
    )
    try:
        with urlopen(req, timeout=10) as resp:
            resp.read()
    except URLError:
        pass
