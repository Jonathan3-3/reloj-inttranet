from django.urls import path
from . import views

urlpatterns = [
    path('', views.lista_reportes, name='lista-reportes'),
    path('generar/', views.generar_reporte, name='generar-reporte'),
    path('plantillas/', views.lista_plantillas, name='lista-plantillas'),
]
