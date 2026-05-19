from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .api_views import (
    CurrentUserAPIView,
    CustomerViewSet,
    ExpenseViewSet,
    LoginAPIView,
    LogoutAPIView,
    MpesaCallbackAPIView,
    PaymentViewSet,
    ProductViewSet,
    RegisterAPIView,
    SalesViewSet,
    StockMovementViewSet,
    LowStockAlertsAPI,
    dashboard_summary_api,
    report_profit_api,
    report_sales_api,
    report_summary_api,
)

router = DefaultRouter()
router.register("products", ProductViewSet, basename="api-product")
router.register("customers", CustomerViewSet, basename="api-customer")
router.register("sales", SalesViewSet, basename="api-sale")
router.register("payments", PaymentViewSet, basename="api-payment")
router.register("expenses", ExpenseViewSet, basename="api-expense")
router.register("stock-movements", StockMovementViewSet, basename="api-stock-movement")

urlpatterns = [
    path("auth/register/", RegisterAPIView.as_view(), name="api-register"),
    path("auth/login/", LoginAPIView.as_view(), name="api-login"),
    path("auth/logout/", LogoutAPIView.as_view(), name="api-logout"),
    path("auth/me/", CurrentUserAPIView.as_view(), name="api-me"),
    path("payments/mpesa/callback/", MpesaCallbackAPIView.as_view(), name="api-mpesa-callback"),
    path("alerts/low-stock/", LowStockAlertsAPI.as_view(), name="api-low-stock-alerts"),
    path("dashboard/", dashboard_summary_api, name="api-dashboard-summary"),
    path("reports/summary/", report_summary_api, name="api-report-summary"),
    path("reports/sales/", report_sales_api, name="api-report-sales"),
    path("reports/profit/", report_profit_api, name="api-report-profit"),
    path("", include(router.urls)),
]
