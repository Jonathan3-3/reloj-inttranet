from django.urls import path
from . import views

urlpatterns = [
    path('', views.lista_solicitudes, name='lista-solicitudes'),
    path('nueva/', views.nueva_solicitud, name='nueva-solicitud'),
    path('<int:pk>/', views.detalle_solicitud, name='detalle-solicitud'),
    path('admin/', views.panel_admin, name='panel-solicitudes'),
    path('admin/<int:pk>/aprobar/', views.aprobar_solicitud, name='aprobar-solicitud'),
    path('admin/<int:pk>/rechazar/', views.rechazar_solicitud, name='rechazar-solicitud'),
    path('api/notificaciones/', views.api_notificaciones, name='api-notificaciones'),
    path('api/notificaciones/<int:pk>/leer/', views.api_marcar_leida, name='api-marcar-leida'),
]
