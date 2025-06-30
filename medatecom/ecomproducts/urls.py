from django.urls import path
from . import views

urlpatterns = [
    path('',views.productlist,name='product_list'),
    
]
