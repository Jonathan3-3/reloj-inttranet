import logging
from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect
from django.contrib.auth.decorators import login_required
from .models import VersionAPK

logger = logging.getLogger(__name__)


def descargar_apk(request):
    apk = VersionAPK.objects.filter(activa=True).first()
    if not apk or not apk.archivo:
        return render(request, 'movil/descargar.html', {
            'error': 'No hay versión disponible para descarga.',
        })
    return render(request, 'movil/descargar.html', {
        'apk': apk,
    })


def descargar_archivo(request):
    apk = VersionAPK.objects.filter(activa=True).first()
    if not apk or not apk.archivo:
        return HttpResponse('No disponible', status=404)
    return HttpResponseRedirect(apk.archivo.url)
