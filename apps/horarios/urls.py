from django.urls import path
from . import views

urlpatterns = [
    path('', views.lista_horarios, name='lista-horarios'),
    path('nuevo/', views.nuevo_horario, name='nuevo-horario'),
    path('<int:pk>/editar/', views.editar_horario, name='editar-horario'),
    path('<int:pk>/asignar/', views.asignar_horario, name='asignar-horario'),
    path('api/horario-empleado/<int:empleado_pk>/', views.api_horario_empleado, name='api-horario-empleado'),
]
