from drf_spectacular.utils import extend_schema
from decimal import Decimal
from django.conf import settings
from django.contrib.auth import login, logout
from django.db.models import Sum
from django.urls import reverse
from rest_framework import filters, status, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.generics import GenericAPIView

from .models import Business, Customer, Expense, Payment, Product, Sales, StockAlert
from .mpesa import MpesaError, initiate_stk_push, parse_stk_callback
from .serializers import (
    CustomerSerializer,
    ExpenseSerializer,
    LoginSerializer,
    PaymentSerializer,
    ProductSerializer,
    RegisterSerializer,
    SaleSerializer,
    UserSerializer,
    EmptySerializer,
    LogoutResponseSerializer,
    DashboardSummarySerializer,
)
from .views import build_dashboard_metrics


def get_or_create_default_business_for_user(user):
    business = Business.objects.filter(owner=user).order_by("id").first()
    if business is not None:
        return business

    display_name = (user.first_name or user.username or "Business").strip()
    if "business" not in display_name.lower():
        display_name = f"{display_name} Business"
    return Business.objects.create(
        owner=user,
        name=display_name[:255],
    )


class RegisterAPIView(GenericAPIView):
    serializer_class = RegisterSerializer
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


class LoginAPIView(GenericAPIView):
    serializer_class = LoginSerializer
    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        login(request, user)
        return Response({"message": "Login successful.", "user": UserSerializer(user).data})

@extend_schema(
    request=EmptySerializer,
    responses=LogoutResponseSerializer
)
class LogoutAPIView(GenericAPIView):
    serializer_class = EmptySerializer
    def post(self, request):
        logout(request)
        return Response({"message": "Logout successful."})


class CurrentUserAPIView(GenericAPIView):
    serializer_class = UserSerializer
    def get(self, request):
        return Response(UserSerializer(request.user).data)


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all().order_by("-created_at")
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "category"]
    ordering_fields = ["created_at", "name", "price", "stock_quantity"]


class CustomerViewSet(viewsets.ModelViewSet):
    queryset = Customer.objects.all().order_by("-created_at")
    serializer_class = CustomerSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "email", "phone"]
    ordering_fields = ["created_at", "name", "email"]


class ExpenseViewSet(viewsets.ModelViewSet):
    queryset = Expense.objects.all().order_by("-date")
    serializer_class = ExpenseSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["description", "category"]
    ordering_fields = ["date", "amount", "category"]


class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.select_related("sale", "business").all().order_by("-payment_date")
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["payment_method", "transaction_id", "phone_number"]
    ordering_fields = ["payment_date", "amount", "payment_method"]

    def _resolve_business(self, serializer):
        supplied_business = serializer.validated_data.get("business")
        if supplied_business is not None:
            return supplied_business
        return get_or_create_default_business_for_user(self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        business = self._resolve_business(serializer)
        if business is None:
            return Response(
                {"detail": "A business is required for payments. Pass a business id or create one for this user."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        payment_method = serializer.validated_data["payment_method"]
        payment = serializer.save(
            business=business,
            status=Payment.STATUS_PENDING if payment_method == "mpesa" else Payment.STATUS_SUCCESS,
        )

        if payment_method != "mpesa":
            response_serializer = self.get_serializer(payment)
            headers = self.get_success_headers(response_serializer.data)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED, headers=headers)

        callback_url = getattr(settings, "MPESA_CALLBACK_URL", "").strip() or request.build_absolute_uri(
            reverse("api-mpesa-callback")
        )

        try:
            stk_response = initiate_stk_push(
                phone_number=payment.phone_number,
                amount=payment.amount,
                account_reference=f"SALE{payment.sale_id}",
                transaction_desc=f"Payment for sale {payment.sale_id}",
                callback_url=callback_url,
            )
        except MpesaError as exc:
            payment.status = Payment.STATUS_FAILED
            payment.result_description = str(exc)
            payment.save(update_fields=["status", "result_description"])
            return Response(
                {"detail": str(exc), "payment": self.get_serializer(payment).data},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        payment.merchant_request_id = stk_response.get("MerchantRequestID")
        payment.checkout_request_id = stk_response.get("CheckoutRequestID")
        payment.result_code = str(stk_response.get("ResponseCode")) if stk_response.get("ResponseCode") is not None else None
        payment.result_description = stk_response.get("ResponseDescription") or stk_response.get("CustomerMessage")
        if payment.result_code not in (None, "0"):
            payment.status = Payment.STATUS_FAILED
        payment.save(
            update_fields=[
                "merchant_request_id",
                "checkout_request_id",
                "result_code",
                "result_description",
                "status",
            ]
        )

        response_serializer = self.get_serializer(payment)
        headers = self.get_success_headers(response_serializer.data)
        return Response(
            {"payment": response_serializer.data, "stk_response": stk_response},
            status=status.HTTP_201_CREATED,
            headers=headers,
        )


class SalesViewSet(viewsets.ModelViewSet):
    queryset = Sales.objects.select_related("customer", "product").all().order_by("-created_at")
    serializer_class = SaleSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["customer__name", "customer__email", "product__name"]
    ordering_fields = ["created_at", "quantity", "price"]

@extend_schema(
    request=None,
    responses=EmptySerializer
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def dashboard_summary_api(GenericAPIView):
    serializer_class = DashboardSummarySerializer

    def get(self, request):

        data = {
            "sales": 100,
            "customers":50,
            "products":20,
            "revenue":5000
        }
        return Response(data)

@extend_schema(
    request=None,
    responses=EmptySerializer
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def report_summary_api(request):
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")

    sales = Sales.objects.select_related("customer", "product").order_by("-created_at")
    payments = Payment.objects.all()
    expenses = Expense.objects.all()

    if start_date and end_date:
        sales = sales.filter(created_at__date__range=[start_date, end_date])
        payments = payments.filter(payment_date__date__range=[start_date, end_date])
        expenses = expenses.filter(date__range=[start_date, end_date])

    total_revenue = payments.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
    total_expenses = expenses.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
    profit = total_revenue - total_expenses

    return Response(
        {
            "start_date": start_date,
            "end_date": end_date,
            "total_sales": sales.count(),
            "total_revenue": float(total_revenue),
            "total_expenses": float(total_expenses),
            "profit": float(profit if profit > 0 else 0),
            "loss": float(abs(profit) if profit < 0 else 0),
        }
    )

@extend_schema(
    request=None,
    responses=EmptySerializer
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def report_sales_api(request):
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")

    sales = Sales.objects.select_related("customer", "product").order_by("-created_at")
    if start_date and end_date:
        sales = sales.filter(created_at__date__range=[start_date, end_date])

    serializer = SaleSerializer(sales, many=True)
    total_revenue = sum(float(sale.total_amount) for sale in sales)

    return Response(
        {
            "start_date": start_date,
            "end_date": end_date,
            "count": sales.count(),
            "total_revenue": total_revenue,
            "results": serializer.data,
        }
    )

@extend_schema(
    request=None,
    responses=EmptySerializer
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def report_profit_api(request):
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")

    payments = Payment.objects.all()
    expenses = Expense.objects.all()

    if start_date and end_date:
        payments = payments.filter(payment_date__date__range=[start_date, end_date])
        expenses = expenses.filter(date__range=[start_date, end_date])

    total_revenue = payments.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
    total_expenses = expenses.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
    profit_value = total_revenue - total_expenses

    return Response(
        {
            "start_date": start_date,
            "end_date": end_date,
            "total_revenue": float(total_revenue),
            "total_expenses": float(total_expenses),
            "profit": float(profit_value),
            "is_profitable": profit_value >= 0,
        }
    )


class MpesaCallbackAPIView(GenericAPIView):
    serializer_class = EmptySerializer
    authentication_classes = []

    def post(self, request):
        callback_data = parse_stk_callback(request.data)
        payment = Payment.objects.filter(
            checkout_request_id=callback_data["checkout_request_id"]
        ).first()

        if payment is None and callback_data["merchant_request_id"]:
            payment = Payment.objects.filter(
                merchant_request_id=callback_data["merchant_request_id"]
            ).first()

        if payment is not None:
            metadata = callback_data["metadata"]
            payment.transaction_id = metadata.get("MpesaReceiptNumber") or payment.transaction_id
            payment.phone_number = str(metadata.get("PhoneNumber") or payment.phone_number or "")
            if metadata.get("Amount") is not None:
                payment.amount = metadata["Amount"]
            payment.result_code = (
                str(callback_data["result_code"])
                if callback_data["result_code"] is not None
                else None
            )
            payment.result_description = callback_data["result_description"]
            payment.callback_payload = request.data
            payment.status = (
                Payment.STATUS_SUCCESS
                if callback_data["result_code"] in (0, "0")
                else Payment.STATUS_FAILED
            )
            payment.save(
                update_fields=[
                    "transaction_id",
                    "phone_number",
                    "amount",
                    "result_code",
                    "result_description",
                    "callback_payload",
                    "status",
                ]
            )

        return Response({"ResultCode": 0, "ResultDesc": "Accepted"})

class LowStockAlertsAPI(GenericAPIView):
    def get(self, request):
        alerts = StockAlert.objects.filter(is_read=False).order_by('-created_at')

        data = [
            {
                "product": a.product.name,
                "message": a.message,
                "date": a.created_at
            }
            for a in alerts
        ]

        return Response(data)
