from django.urls import path
from . import views

urlpatterns = [
    path('', views.lista_empleados, name='lista-empleados'),
    path('nuevo/', views.nuevo_empleado, name='nuevo-empleado'),
    path('<int:pk>/', views.detalle_empleado, name='detalle-empleado'),
    path('<int:pk>/editar/', views.editar_empleado, name='editar-empleado'),
    path('<int:pk>/renuncia/', views.renuncia_empleado, name='renuncia-empleado'),
    path('<int:pk>/recontratar/', views.recontratar_empleado, name='recontratar-empleado'),
    path('api/buscar/', views.buscar_empleados_api, name='buscar-empleados-api'),
    path('importar/', views.importar_csv, name='importar-csv'),
]
