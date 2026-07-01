from django.urls import path
from . import views

urlpatterns = [
    path('', views.lista_horarios, name='lista-horarios'),
    path('nuevo/', views.nuevo_horario, name='nuevo-horario'),
    path('<int:pk>/editar/', views.editar_horario, name='editar-horario'),
    path('<int:pk>/asignar/', views.asignar_horario, name='asignar-horario'),
    path('asignacion-masiva/', views.asignacion_masiva, name='asignacion-masiva'),
    path('api/horario-empleado/<int:empleado_pk>/', views.api_horario_empleado, name='api-horario-empleado'),
    path('api/departamentos/<int:area_id>/', views.api_departamentos_por_area, name='api-departamentos-por-area'),
    path('api/empleados-por-filtro/', views.api_empleados_por_filtro, name='api-empleados-por-filtro'),
]
