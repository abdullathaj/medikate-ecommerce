from django.urls import path
from . import views

urlpatterns = [
    path('', views.orderlist, name='order_list'),
    path('buy-now/<int:variant_id>/', views.buy_now, name='buy_now'),
    path('payment-method/', views.payment_method, name='payment_method'),
    path('order-success/<int:order_id>/', views.order_success, name='order_success'),  
    path('order-details/<int:order_id>/', views.order_details, name='order_details'),

]