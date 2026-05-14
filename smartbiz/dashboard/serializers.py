from django.contrib.auth import authenticate
from rest_framework import serializers

from .models import Business, Customer, Expense, Payment, Product, Sales, User


class UserSerializer(serializers.ModelSerializer):
    effective_role = serializers.CharField(read_only=True)
    role_label = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "role",
            "effective_role",
            "role_label",
        ]


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True, min_length=8)
    name = serializers.CharField(write_only=True, max_length=150)

    class Meta:
        model = User
        fields = ["name", "email", "password", "confirm_password"]

    def validate_email(self, value):
        email = value.strip().lower()
        if User.objects.filter(username=email).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return email

    def validate(self, attrs):
        if attrs["password"] != attrs["confirm_password"]:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})
        return attrs

    def create(self, validated_data):
        email = validated_data["email"]
        name = validated_data["name"].strip()
        password = validated_data["password"]
        return User.objects.create_user(
            username=email,
            email=email,
            password=password,
            first_name=name,
            role=User.BUSINESS_OWNER,
        )


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        email = attrs["email"].strip().lower()
        password = attrs["password"]
        user = authenticate(
            request=self.context.get("request"),
            username=email,
            password=password,
        )
        if user is None:
            raise serializers.ValidationError("Invalid email or password.")
        attrs["user"] = user
        return attrs

class LogoutResponseSerializer(serializers.Serializer):
    message = serializers.CharField()
    
class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ["id", "name", "email", "phone", "created_at"]
        read_only_fields = ["id", "created_at"]


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ["id", "name", "category", "price", "stock_quantity", "created_at"]
        read_only_fields = ["id", "created_at"]


class ExpenseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Expense
        fields = ["id", "description", "amount", "category", "date"]
        read_only_fields = ["id", "date"]


class PaymentSerializer(serializers.ModelSerializer):
    status = serializers.CharField(read_only=True)
    merchant_request_id = serializers.CharField(read_only=True)
    checkout_request_id = serializers.CharField(read_only=True)
    result_code = serializers.CharField(read_only=True)
    result_description = serializers.CharField(read_only=True)
    callback_payload = serializers.JSONField(read_only=True)
    business = serializers.PrimaryKeyRelatedField(queryset=Business.objects.all(), required=False)

    class Meta:
        model = Payment
        fields = [
            "id",
            "sale",
            "business",
            "amount",
            "payment_method",
            "transaction_id",
            "merchant_request_id",
            "checkout_request_id",
            "status",
            "result_code",
            "result_description",
            "callback_payload",
            "payment_date",
            "phone_number",
        ]
        read_only_fields = ["id", "payment_date"]

    def validate(self, attrs):
        payment_method = attrs.get("payment_method", getattr(self.instance, "payment_method", None))
        phone_number = attrs.get("phone_number", getattr(self.instance, "phone_number", None))
        amount = attrs.get("amount", getattr(self.instance, "amount", None))

        if amount is not None and amount <= 0:
            raise serializers.ValidationError({"amount": "Amount must be greater than zero."})

        if payment_method == "mpesa" and not phone_number:
            raise serializers.ValidationError({"phone_number": "Phone number is required for M-Pesa payments."})
        return attrs


class SaleSerializer(serializers.ModelSerializer):
    customer = CustomerSerializer(read_only=True)
    product = ProductSerializer(read_only=True)
    customer_id = serializers.PrimaryKeyRelatedField(
        queryset=Customer.objects.all(),
        source="customer",
        write_only=True,
    )
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(),
        source="product",
        write_only=True,
    )
    total_amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = Sales
        fields = [
            "id",
            "customer",
            "product",
            "customer_id",
            "product_id",
            "quantity",
            "price",
            "total_amount",
            "created_at",
        ]
        read_only_fields = ["id", "created_at", "total_amount"]

    def validate_quantity(self, value):
        if value <= 0:
            raise serializers.ValidationError("Quantity must be greater than zero.")
        return value

    def validate_price(self, value):
        if value <= 0:
            raise serializers.ValidationError("Price must be greater than zero.")
        return value

class EmptySerializer(serializers.Serializer):

    pass