from django.urls import path
from . import views



urlpatterns = [
    path('',views.admin_dashboard,name='admin_dashboard'),
    # ADMIN USER MANAGEMENT
    path('customer_details/',views.admin_customer_details,name='customer_details'),
    path('add_user/',views.admin_add_user,name='add_user'),
    path('block_user/<int:user_id>/',views.admin_block_user,name='block_user'),
    # ADMIN CATEGORY MANAGEMENT
    path('admin_categories/',views.admin_category_list,name='admin_categories'),
    path('admin_add_category/',views.admin_add_category,name='admin_add_category'),
    path('admin_hide_category/<int:category_id>/',views.admin_hide_category,name='admin_hide_category'),
    path('admin_edit_category/<int:category_id>/',views.admin_edit_category,name='admin_edit_category'),
    # ADMIN PRODUCT MANAGEMENT
    path('admin_product_list/',views.admin_product_details,name='admin_product_list'),
    path('admin_add_product/',views.admin_add_product,name='admin_add_product'),
    path('admin_edit_product/<int:product_id>',views.admin_edit_product,name='admin_edit_product'),
    path('admin_hide_product/<int:variant_id>/',views.admin_hide_product,name='admin_hide_product'),

    # ADMIN ORDER MANAGEMENT
    path('admin_order_list/',views.admin_order_list,name='admin_order_list'),
    path('admin_order_item_list/<int:order_id>/',views.admin_order_item_list,name='admin_order_item_list'),
    path('admin_edit_order_status/<int:item_id>/', views.admin_edit_order_status, name='admin_edit_order_status'),  
    path('admin_return_approval/<int:request_id>/',views.admin_return_approval, name='admin_return_approval'), 
    path('admin_request_list/', views.admin_request_list, name='admin_request_list'),

    # ADMIN COUPON MANAGEMENT
    path('admin_coupon_list/',views.admin_coupon_list, name='admin_coupon_list'),
    path('admin_add_coupon', views.admin_coupon_creation, name='admin_coupon_creation'),
    path('admin_delete_coupon/<int:coupon_id>/', views.admin_coupon_delete, name='admin_coupon_delete'),
    path('admin_edit_coupon/<int:coupon_id>/', views.admin_coupon_edit, name='admin_coupon_edit'),

    # ADMIN OFFER MANAGEMENT
    path('admin_offer_list/', views.admin_offer_list, name='admin_offer_list'),
    path('admin_add_offer/', views.admin_offer_creation, name='admin_add_offer'),
    path('admin_delete_offer/<int:offer_id>/', views.admin_offer_delete, name='admin_offer_delete'),

    path('admin_sales_report/', views.admin_sales_report, name='admin_sales_report'),


]
