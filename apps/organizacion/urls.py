from django.urls import path
from . import views

urlpatterns = [
    path('areas/', views.lista_areas, name='lista-areas'),
    path('areas/nueva/', views.nueva_area, name='nueva-area'),
    path('areas/<int:pk>/editar/', views.editar_area, name='editar-area'),
    path('departamentos/', views.lista_departamentos, name='lista-departamentos'),
    path('departamentos/nuevo/', views.nuevo_departamento, name='nuevo-departamento'),
    path('departamentos/<int:pk>/editar/', views.editar_departamento, name='editar-departamento'),
]
