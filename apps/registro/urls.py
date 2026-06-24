from django.urls import path
from . import views

urlpatterns = [
    path('', views.checkin_view, name='checkin'),
    path('api/register/', views.api_register, name='api-register'),
    path('api/ping/', views.api_ping, name='api-ping'),
]
