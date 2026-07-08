from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.api_login, name='api-login'),
    path('me/', views.api_me, name='api-me'),
    path('cambiar-password/', views.api_cambiar_password, name='api-cambiar-password'),
    path('logout/', views.api_logout, name='api-logout'),
    path('solicitudes/', views.api_solicitudes, name='api-solicitudes'),
    path('checkin-status/', views.api_checkin_status, name='api-checkin-status'),
]
