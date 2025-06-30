from django.urls import path
from . import views

urlpatterns = [
    path('',views.admin_dashboard,name='admin_dashboard'),
    path('customer_details/',views.admin_customer_details,name='customer_details'),
    path('add_user/',views.admin_add_user,name='add_user'),
    path('edit_user/<int:user_id>/',views.admin_edit_user,name='edit_user'),
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
    path('admin_hide_product/<int:varient_id>/',views.admin_hide_product,name='admin_hide_product'),
   

]
