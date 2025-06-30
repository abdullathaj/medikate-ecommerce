from django.urls import path
from . import views

urlpatterns = [
    path('',views.orderlist,name='order_list'),
    
]
