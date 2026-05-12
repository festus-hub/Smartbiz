"""
URL configuration for smartbiz project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.urls import include, path
from dashboard import views

if settings.HAS_DRF_SPECTACULAR:
    from drf_spectacular.views import (
        SpectacularAPIView,
        SpectacularSwaggerView,
        SpectacularRedocView,
    )
urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.landing_page, name='landing'),
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('payments/', views.payments_view, name='payments'),
    path('payments/<int:payment_id>/receipt/', views.payment_receipt, name='payment_receipt'),
    path('add-expense/', views.add_expense, name='add_expense'),
    path('sales/', views.sales_view, name='sales'),
    path('api/sales/live/', views.sales_live_api, name='sales-live'),

    path('customers/', views.customers_view, name='customers'),
    path('customers/add/',views.add_customer,name='add_customer'),
    path('customers/edit/<int:id>/', views.edit_customer, name='edit_customer'),
    path('customers/delete/<int:customer_id>/', views.delete_customer, name='delete_customer'),

    path('add_sale/', views.add_sale, name='add_sale'),
    path('sales/<int:sale_id>/edit/', views.edit_sale, name='edit_sale'),
    path('sales/<int:sale_id>/delete/', views.delete_sale, name='delete_sale'),

    path('reports/', views.reports, name='reports'),
    path("api/dashboard/live/", views.dashboard_live_api, name="dashboard-live"),
    path("api/", include("dashboard.api_urls")),
    path('password-reset/', views.custom_password_reset, name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view( template_name='dashboard/password_reset_done.html', ),name='password_reset_done',),
    path('reset/<uidb64>/<token>/',auth_views.PasswordResetConfirmView.as_view(template_name='dashboard/password_reset_confirm.html', ), name='password_reset_confirm',),
    path('reset/done/',auth_views.PasswordResetCompleteView.as_view(template_name='dashboard/password_reset_complete.html',), name='password_reset_complete', ),

    path('products/', views.product_list, name='product_list'),
    path('products/add/', views.add_product, name='add_product'),
    path('products/edit/<int:pk>/', views.edit_product, name='edit_product'),
    path('products/delete/<int:pk>/', views.delete_product, name='delete_product'),

    ]

if settings.HAS_DRF_SPECTACULAR:
    urlpatterns += [
        path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
        path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
        path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    ]
