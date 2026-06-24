from django.urls import path
from . import views

urlpatterns = [
    path('', views.lista_incidencias, name='lista-incidencias'),
    path('tipos/', views.lista_tipos, name='lista-tipos'),
    path('nuevo/', views.nueva_incidencia, name='nueva-incidencia'),
    path('<int:pk>/justificar/', views.justificar_incidencia, name='justificar-incidencia'),
    path('api/tipos/', views.api_tipos_incidencia, name='api-tipos-incidencia'),
    path('api/empleado/<int:empleado_pk>/', views.api_incidencias_empleado, name='api-incidencias-empleado'),
]
