from django.urls import path
from . import views

app_name = 'movil'

urlpatterns = [
    path('descargar/', views.descargar_apk, name='descargar'),
    path('descargar/archivo/', views.descargar_archivo, name='descargar_archivo'),
]
