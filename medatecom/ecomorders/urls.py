from django.urls import path
from . import views

urlpatterns = [
    path('', views.orderlist, name='order_list'),
    path('buy-now/<int:variant_id>/', views.buy_now, name='buy_now'),
    path('payment-method/', views.payment_method, name='payment_method'),
    path('order-success/<int:order_id>/', views.order_success, name='order_success'),  
    path('order-details/<int:order_id>/<int:item_id>/', views.order_details, name='order_details'),
    path('checkout/', views.checkout, name='checkout'),
    path('cancel-order-item/<int:order_id>/<int:item_id>/', views.cancel_order_item, name='cancel_order_item'),
    path('return-order-item/<int:order_id>/<int:item_id>/', views.return_order_item, name='return_order_item'),
    path('razorpay_success/',views.razorpay_success,name='razorpay_success'),
    path('order_error/',views.order_error,name='order_error'),
]


