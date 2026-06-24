from django.urls import path
from . import views

urlpatterns = [
    path('', views.buscar_asistencia, name='buscar-asistencia'),
    path('hoy/', views.vista_hoy, name='vista-hoy'),
    path('empleado/<int:pk>/', views.detalle_asistencia, name='detalle-asistencia'),
    path('api/reporte/', views.api_reporte, name='api-reporte'),
    path('api/reporte/excel/', views.api_reporte_excel, name='api-reporte-excel'),
    path('api/today/', views.api_today, name='api-today'),
    path('api/empleados/', views.api_empleados, name='api-empleados'),
    path('api/recalcular/<int:empleado_pk>/', views.api_recalcular, name='api-recalcular'),
]
