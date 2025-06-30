from django.urls import path
from . import views
from django.contrib.auth.views import PasswordResetView,PasswordResetDoneView, PasswordResetConfirmView, PasswordResetCompleteView

urlpatterns = [
    path('login/',views.loginview, name='login'),
    path('register/',views.registerview, name='register'),
    path('logout/',views.logout_view, name='logout'),
    path('otp_verify/',views.otp_verify_view, name='otp_verify'),
    path('resend_otp/',views.resend_otp_view, name='resend_otp'),
    path('forgot_password/',views.forgot_password_view, name='forgot_password'),
    path('reset_password/',views.reset_password_view, name='reset_password'),
    path('resend_password_otp/',views.resend_password_otp_view, name='resend_password_otp'),
    # admin
    path('admin_login/', views.admin_login_view, name='admin_login'),
    path('admin_dashboard/', views.admin_dashboard_view, name='admin_dashboard'),
    path('admin_logout/', views.admin_logout_view, name='admin_logout')




    
]

