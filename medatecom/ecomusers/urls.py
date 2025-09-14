from django.urls import path
from . import views

urlpatterns = [
    path('',views.userhomeview,name='userhome'),
    path('login_home/',views.home_after_login,name='login_home'),

    path('product_details/<int:variant_id>/',views.product_details,name='product_details'),
    path('product_listing/',views.user_product_listing,name='product_listing'),
    # PRODUCT CARD BUTTONS
    path('add_to_cart/<int:variant_id>/', views.add_to_cart, name='add_to_cart'),
    path('add_to_wishlist/<int:variant_id>/', views.add_to_wishlist, name='add_to_wishlist'),
    path('remove_from_wishlist/', views.remove_from_wishlist, name='remove_from_wishlist'),


    # NAVBAR BUTTONS
    path('user_cart/',views.users_cart_page,name='user_cart_page'),
    path('user_profile/',views.users_profile_page,name='user_profile_page'),
    path('user_wishlist/',views.users_wishlist_page,name='user_wishlist_page'),
    path('user_wallet/',views.users_wallet_page,name='user_wallet_page'),
    # PROFILE EDITING 
    path('user_profile_update/',views.users_profile_update_page,name='user_profile_update'),
    path('delete-address/<int:address_id>/', views.user_delete_address, name='delete_address'),
    path('edit-address/<int:address_id>/', views.user_edit_address, name='edit_address'),
    path('verify_email_otp/',views.verify_email_otp, name='verify_email_otp'),

    
    # CART FEATURES
    path('update_cart_quantity/<int:cart_item_id>/',views.update_cart_quantity,name='update_cart_quantity'),
    path('remove_cart_item/<int:cart_item_id>/',views.remove_cart_item,name='remove_cart_item'),
    path('save_for_later/<int:cart_item_id>/',views.save_for_later,name='save_for_later'),
    # path('cart_select_address/',views.cart_select_address,name='cart_select_address'),
    
    


]
