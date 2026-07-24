from django.db import models

class VersionAPK(models.Model):
    version = models.CharField('Versión', max_length=20)
    archivo = models.FileField('Archivo APK', upload_to='apk/',
                               help_text='Subir archivo .apk')
    notas = models.TextField('Notas de la versión', blank=True, default='')
    activa = models.BooleanField('Activa', default=True,
                                  help_text='Solo la versión activa se ofrece para descarga')
    peso_mb = models.DecimalField('Peso (MB)', max_digits=5, decimal_places=2,
                                   editable=False, default=0)
    creado_en = models.DateTimeField('Creado en', auto_now_add=True)

    class Meta:
        verbose_name = 'Versión APK'
        verbose_name_plural = 'Versiones APK'
        db_table = 'versiones_apk'
        ordering = ['-creado_en']

    def save(self, *args, **kwargs):
        if self.archivo and hasattr(self.archivo, 'size'):
            self.peso_mb = self.archivo.size / (1024 * 1024)
        if self.activa:
            VersionAPK.objects.filter(activa=True).exclude(pk=self.pk).update(activa=False)
        super().save(*args, **kwargs)

    def __str__(self):
        return f'APK v{self.version} ({self.creado_en.date()})'
