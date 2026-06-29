from django.urls import path
from . import views

urlpatterns = [
    path('', views.checkin_view, name='checkin'),
    path('api/register/', views.api_register, name='api-register'),
    path('api/ping/', views.api_ping, name='api-ping'),
    path('iclock/getrequest', views.iclock_getrequest, name='iclock-getrequest'),
    path('iclock/cdata', views.iclock_cdata, name='iclock-cdata'),
    path('iclock/device', views.iclock_device, name='iclock-device'),
]
