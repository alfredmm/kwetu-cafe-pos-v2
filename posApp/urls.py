from . import views
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path
from django.views.generic.base import RedirectView


urlpatterns = [
    path('redirect-admin', RedirectView.as_view(url="/admin"),name="redirect-admin"),
    path('', views.home, name="home-page"),
    path('login', auth_views.LoginView.as_view(template_name = 'posApp/login.html',redirect_authenticated_user=True), name="login"),
    path('userlogin', views.login_user, name="login-user"),
    path('logout', views.logoutuser, name="logout"),
    path('category', views.category, name="category-page"),
    path('manage_category', views.manage_category, name="manage_category-page"),
    path('save_category', views.save_category, name="save-category-page"),
    path('delete_category', views.delete_category, name="delete-category"),
    path('products', views.products, name="product-page"),
    path('manage_products', views.manage_products, name="manage_products-page"),
    #path('test', views.test, name="test-page"),
    path('save_product', views.save_product, name="save-product-page"),
    path('delete_product', views.delete_product, name="delete-product"),
    path('pos', views.pos, name="pos-page"),
    path('checkout-modal', views.checkout_modal, name="checkout-modal"),
    path('save-pos', views.save_pos, name="save-pos"),
    path('sales', views.salesList, name="sales-page"),
    path('receipt', views.receipt, name="receipt-modal"),
    path('delete_sale', views.delete_sale, name="delete-sale"),
    path('get-chart-data', views.get_chart_data, name="get-chart-data"),
    
    path('users/', views.user_list, name='user_list'),
    path('users/create/', views.user_create, name='user_create'),
    path('users/edit/', views.user_edit, name='user_edit'),
    path('users/delete/', views.user_delete, name='user_delete'),
    path('users/toggle-status/<int:user_id>/', views.user_toggle_status, name='user_toggle_status'),

    # Employee Management URLs
    path('employees/', views.employee_list, name='employee_list'),
    path('employees/create/', views.employee_create, name='employee_create'),
    path('employees/<int:emp_id>/edit/', views.employee_edit, name='employee_edit'),
    path('employees/<int:emp_id>/delete/', views.employee_delete, name='employee_delete'),
]