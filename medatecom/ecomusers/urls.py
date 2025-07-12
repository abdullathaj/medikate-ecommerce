from django.urls import path
from . import views

urlpatterns = [
    path('',views.userhomeview,name='userhome'),
   
    path('login_home/',views.home_after_login,name='login_home'),
    path('product_details/<int:product_id>/',views.product_details,name='product_details'),

]
