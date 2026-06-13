from django.urls import path
from . import views

urlpatterns = [
    path('auth/register-request/', views.register_request, name='register-request'),
    path('auth/verify-ceo/', views.verify_ceo, name='verify-ceo'),
    path('auth/create-company/', views.create_company, name='create-company'),
    path('auth/login/', views.login_employee, name='saas-login'),
    path('auth/forget-password/', views.forget_password, name='forget-password'),
    path('auth/reset-password/', views.reset_password, name='reset-password'),
]