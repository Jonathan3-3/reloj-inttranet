from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('api/stats/', views.api_stats, name='api-stats'),
    path('ruta/', views.mapa_ruta, name='mapa-ruta'),
]
