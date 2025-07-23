from django.urls import path
from . import views

urlpatterns = [
    path('',views.userhomeview,name='userhome'),
   
    path('login_home/',views.home_after_login,name='login_home'),
    path('product_details/<int:product_id>/',views.product_details,name='product_details'),
    path('product_listing/',views.user_product_listing,name='product_listing'),
    path('user_cart/',views.users_cart_page,name='user_cart_page'),
    path('user_profile/',views.users_profile_page,name='user_profile_page'),
    path('user_orders/',views.users_orders_page,name='user_orders_page'),
    path('user_wishlist/',views.users_wishlist_page,name='user_wishlist_page'),
    path('user_wallet/',views.users_wallet_page,name='user_wallet_page'),


]
