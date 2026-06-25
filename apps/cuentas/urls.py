from django.urls import path
from django.contrib.auth.views import LogoutView
from . import views

urlpatterns = [
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('profile/', views.profile, name='profile'),
    path('cambiar-password/', views.cambiar_password, name='cambiar-password'),
    path('restablecer-contrasena/<int:user_id>/', views.restablecer_contrasena, name='restablecer-contrasena'),
]
