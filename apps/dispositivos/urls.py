from django.urls import path
from . import views

urlpatterns = [
    path('', views.lista_dispositivos, name='lista-dispositivos'),
    path('conexiones/', views.conexiones_activas, name='conexiones-activas'),
    path('api/estado/', views.api_estado_dispositivos, name='api-estado-dispositivos'),
    path('api/sincronizar/<int:pk>/', views.api_sincronizar, name='api-sincronizar'),
]
