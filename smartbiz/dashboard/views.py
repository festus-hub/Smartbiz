import csv
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth import authenticate, login, logout
from decimal import Decimal
from django.db.models import F, Sum
from django.urls import reverse
from django.utils.dateparse import parse_date
from functools import wraps
from .models import Sales, Payment, Customer, User, Product, Expense, StockMovement
from . import models
from django.contrib.auth.forms import PasswordResetForm
from .forms import ProductForm, StockMovementForm
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import serializers

try:
    from drf_spectacular.utils import extend_schema, OpenApiResponse, inline_serializer
except ImportError:
    def extend_schema(*args, **kwargs):
        def decorator(func):
            return func
        return decorator

    class OpenApiResponse:
        def __init__(self, description=''):
            self.description = description

    def inline_serializer(*args, **kwargs):
        return serializers.DictField()


# LANDING PAGE

def landing_page(request):
    return render(request, 'dashboard/landing.html')


def role_required(minimum_role):
    def decorator(view_func):
        @login_required(login_url='login')
        @wraps(view_func)
        def wrapped_view(request, *args, **kwargs):
            if not request.user.has_minimum_role(minimum_role):
                raise PermissionDenied("You do not have permission to access this page.")
            return view_func(request, *args, **kwargs)
        return wrapped_view
    return decorator


def build_dashboard_metrics():
    total_sales = Sales.objects.count()
    total_customers = Customer.objects.count()
    total_products = Product.objects.count()
    sales = list(Sales.objects.select_related('customer', 'product').order_by('-created_at'))
    total_revenue = sum((sale.total_amount for sale in sales), Decimal('0.00'))
    total_expenses = Expense.objects.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

    profit = total_revenue - total_expenses

    monthly_revenue = [0] * 12
    monthly_expenses = [0] * 12

    expenses = Expense.objects.all()

    for sale in sales:
        month = sale.created_at.month - 1
        monthly_revenue[month] += float(sale.total_amount)

    for exp in expenses:
        month = exp.date.month - 1
        monthly_expenses[month] += float(exp.amount)

    sales_distribution_qs = (
        Sales.objects.values('product__name')
        .annotate(total_quantity=Sum('quantity'))
        .order_by('-total_quantity')[:5]
    )

    sales_distribution = {
        'labels': [item['product__name'] for item in sales_distribution_qs],
        'values': [item['total_quantity'] or 0 for item in sales_distribution_qs],
    }

    recent_sales = [
        {
            'customer__name': sale.customer.name,
            'product__name': sale.product.name,
            'price': float(sale.total_amount),
            'created_at': sale.created_at.strftime('%Y-%m-%d'),
        }
        for sale in sales[:5]
    ]

    pending_payment = Sales.objects.filter(payments__isnull=True).count()

    return {
        'total_sales': total_sales,
        'total_customers': total_customers,
        'total_products': total_products,
        'total_revenue': float(total_revenue),
        'total_expenses': float(total_expenses),
        'profit': float(profit if profit > 0 else 0),
        'loss': float(abs(profit) if profit < 0 else 0),
        'monthly_revenue': monthly_revenue,
        'monthly_expenses': monthly_expenses,
        'sales_distribution': sales_distribution,
        'recent_sales': recent_sales,
        'pending_payment': pending_payment,
    }


def build_sales_metrics():
    sales_qs = Sales.objects.select_related('customer', 'product').order_by('-created_at')
    sales = list(sales_qs)
    total_sales = len(sales)
    total_revenue = sum(float(sale.total_amount) for sale in sales)

    sales_rows = [
        {
            'id': sale.id,
            'product': str(sale.product),
            'customer': str(sale.customer),
            'quantity': sale.quantity,
            'amount': float(sale.total_amount),
            'created_at': sale.created_at.strftime('%b %d, %Y %H:%M'),
            'edit_url': reverse('edit_sale', args=[sale.id]),
            'delete_url': reverse('delete_sale', args=[sale.id]),
        }
        for sale in sales
    ]

    return {
        'sales': sales,
        'sales_rows': sales_rows,
        'total_sales': total_sales,
        'transactions': total_sales,
        'total_revenue': total_revenue,
    }


def validate_stock_movement(product, quantity, movement_type):
    if quantity <= 0:
        return "Quantity must be greater than zero."
    if movement_type == StockMovement.MOVEMENT_OUT and quantity > product.stock_quantity:
        return f"Cannot remove {quantity} units from {product.name}. Only {product.stock_quantity} available."
    return None


def create_stock_movement(*, product, quantity, movement_type, note=''):
    error = validate_stock_movement(product, quantity, movement_type)
    if error:
        raise ValueError(error)

    return StockMovement.objects.create(
        product=product,
        quantity=quantity,
        movement_type=movement_type,
        note=note,
    )


# AUTH VIEWS

def login_view(request):
    if request.method == 'POST':
        username = (request.POST.get('username') or '').strip()
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect('dashboard')
        else:
            messages.error(request, "Invalid email or password")
            return redirect('login')

    return render(request, 'dashboard/login.html')


def logout_view(request):
    logout(request)
    return redirect('landing')


def register_view(request):
    if request.method == "POST":
        name = (request.POST.get("username") or '').strip()
        email = (request.POST.get("email") or '').strip().lower()
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")

        if not email:
            messages.error(request, "Email is required")
            return redirect("register")

        if not password:
            messages.error(request, "Password is required")
            return redirect("register")

        if password != confirm_password:
            messages.error(request, "Passwords do not match")
            return redirect("register")

        if User.objects.filter(username=email).exists():
            messages.error(request, "User already exists")
            return redirect("register")

        user = User.objects.create_user(
            username=email,
            email=email,
            password=password,
            first_name=name,
            role=User.BUSINESS_OWNER,
        )
        user.save()

        login(request, user, backend='django.contrib.auth.backends.ModelBackend')
        messages.success(request, "Account created successfully")
        return redirect("login")

    return render(request, 'dashboard/register.html')



# DASHBOARD VIEWS

@role_required(User.EMPLOYEE)
def dashboard(request):
    context = build_dashboard_metrics()
    return render(request, 'dashboard/index.html', context)


@extend_schema(
    summary="Live Dashboard Metrics",
    description=(
        "Returns real-time dashboard data including total sales, customers, products, "
        "revenue, expenses, profit/loss, monthly breakdowns, sales distribution, "
        "recent sales, and pending payments. Requires authentication."
    ),
    responses={
        200: inline_serializer(
            name='DashboardMetrics',
            fields={
                'total_sales': serializers.IntegerField(),
                'total_customers': serializers.IntegerField(),
                'total_products': serializers.IntegerField(),
                'total_revenue': serializers.FloatField(),
                'total_expenses': serializers.FloatField(),
                'profit': serializers.FloatField(),
                'loss': serializers.FloatField(),
                'monthly_revenue': serializers.ListField(child=serializers.FloatField()),
                'monthly_expenses': serializers.ListField(child=serializers.FloatField()),
                'pending_payments': serializers.IntegerField(),
            }
        ),
        401: OpenApiResponse(description='Unauthorized - login required'),
    },
    tags=['Dashboard'],
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_live_api(request):
    """
    Returns live dashboard metrics for the authenticated user.
    Used by the dashboard page to refresh stats without a full page reload.
    """
    return Response(build_dashboard_metrics())


# PAYMENTS VIEW


@role_required(User.CASHIER)
def payments_view(request):
    amount = Payment.objects.aggregate(total=Sum('amount'))['total'] or 0
    payment_methods = Payment.PAYMENT_METHODS
    payments = Payment.objects.select_related('sale', 'business').order_by('-payment_date')
    sales = Sales.objects.select_related('customer', 'product').order_by('-created_at')
    businesses = models.Business.objects.select_related('owner').order_by('name')
    status_filter = (request.GET.get('status') or '').strip()
    method_filter = (request.GET.get('method') or '').strip()
    query = (request.GET.get('q') or '').strip()

    if status_filter:
        payments = payments.filter(status=status_filter)

    if method_filter:
        payments = payments.filter(payment_method=method_filter)

    if query:
        payments = payments.filter(
              models.Q(transaction_id__icontains=query)
            | models.Q(checkout_request_id__icontains=query)
            | models.Q(phone_number__icontains=query)
            | models.Q(sale__customer__name__icontains=query)
            | models.Q(business__name__icontains=query)
        )

    transaction_ids = payments.values_list('transaction_id', flat=True).distinct()
    payment_dates = payments.values_list('payment_date', flat=True).distinct()
    context = {
        'payments': payments,
        'sales': sales,
        'businesses': businesses,
        'amount': amount,
        'payment_methods': payment_methods,
        'payment_statuses': Payment.STATUS_CHOICES,
        'selected_status': status_filter,
        'selected_method': method_filter,
        'search_query': query,
        'transaction_ids': transaction_ids,
        'payment_dates': payment_dates,
    }
    return render(request, 'dashboard/payment.html', context)


@role_required(User.CASHIER)
def payment_receipt(request, payment_id):
    payment = get_object_or_404(
        Payment.objects.select_related('sale__customer', 'sale__product', 'business'),
        id=payment_id,
    )
    return render(request, 'dashboard/payment_receipt.html', {'payment': payment})


# EXPENSE VIEW

@role_required(User.MANAGER)
def add_expense(request):
    if request.method == 'POST':
        description = (request.POST.get('description') or '').strip()
        category = (request.POST.get('category') or '').strip()

        try:
            amount = float(request.POST.get('amount'))
        except (TypeError, ValueError):
            messages.error(request, "Enter a valid expense amount.")
            return redirect('add_expense')

        if not description:
            messages.error(request, "Expense description is required.")
            return redirect('add_expense')

        if amount <= 0:
            messages.error(request, "Expense amount must be greater than zero.")
            return redirect('add_expense')

        Expense.objects.create(
            description=description,
            amount=amount,
            category=category or 'other',
        )

        messages.success(request, "Expense added successfully.")
        return redirect('dashboard')

    context = {
        'categories': Expense.CATEGORY_CHOICES,
    }
    return render(request, 'dashboard/add_expense.html', context)


# SALES VIEWS

@role_required(User.CASHIER)
def sales_view(request):
    context = build_sales_metrics()
    return render(request, 'dashboard/sales.html', context)


@extend_schema(
    summary="Live Sales Data",
    description=(
        "Returns real-time sales data including a list of all sales rows, "
        "total sale count, number of transactions, and total revenue. "
        "Requires authentication."
    ),
    responses={
        200: inline_serializer(
            name='SalesMetrics',
            fields={
                'total_sales': serializers.IntegerField(),
                'transactions': serializers.IntegerField(),
                'total_revenue': serializers.FloatField(),
                'sales': serializers.ListField(
                    child=inline_serializer(
                        name='SaleRow',
                        fields={
                            'id': serializers.IntegerField(),
                            'product': serializers.CharField(),
                            'customer': serializers.CharField(),
                            'quantity': serializers.IntegerField(),
                            'amount': serializers.FloatField(),
                            'created_at': serializers.CharField(),
                            'edit_url': serializers.CharField(),
                            'delete_url': serializers.CharField(),
                        }
                    )
                ),
            }
        ),
        401: OpenApiResponse(description='Unauthorized - login required'),
    },
    tags=['Sales'],
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def sales_live_api(request):
    """
    Returns live sales metrics for the authenticated user.
    Used by the sales page to refresh data without a full page reload.
    """
    data = build_sales_metrics()
    return Response({
        'sales': data['sales_rows'],
        'total_sales': data['total_sales'],
        'transactions': data['transactions'],
        'total_revenue': data['total_revenue'],
    })



# CUSTOMERS VIEWS

@role_required(User.EMPLOYEE)
def customers_view(request):
    query = request.GET.get('q', '')

    customers = models.Customer.objects.all().order_by('-created_at')

    # Search filter
    if query:
        customers = customers.filter(
            name__icontains=query
        )

    total_customers = models.Customer.objects.count()

    active_customers = models.Customer.objects.count()

    context = {
        'customers': customers,
        'total_customers': total_customers,
        'active_customers': active_customers,
        'query': query,
    }

    return render(request, 'dashboard/customer.html', context)

@role_required(User.EMPLOYEE)
def add_customer(request):
    if request.method == 'POST':
        name = (request.POST.get('name') or '').strip()
        phone = (request.POST.get('phone') or '').strip()
        email = (request.POST.get('email') or '').strip().lower()

        if not name:
            messages.error(request, "Customer name is required.")
            return redirect('add_customer')

        if not email:
            messages.error(request, "Customer email is required.")
            return redirect('add_customer')

        if Customer.objects.filter(email=email).exists():
            messages.error(request, "A customer with this email already exists.")
            return redirect('add_customer')

        Customer.objects.create(
            name=name,
            phone=phone,
            email=email,
        )

        messages.success(request, "Customer added successfully.")
        return redirect('customers')
    return render(request, 'dashboard/add_customer.html')   

def upsert_customer(customer_name, phone, email, current_customer=None):
    email = (email or '').strip().lower()
    customer_name = (customer_name or '').strip()
    phone = (phone or '').strip()

    if current_customer and current_customer.email == email:
        customer = current_customer
        created = False
    else:
        customer, created = Customer.objects.get_or_create(
            email=email,
            defaults={
                'name': customer_name,
                'phone': phone,
            }
        )

    customer_updated = False
    if customer.name != customer_name and customer_name:
        customer.name = customer_name
        customer_updated = True
    if customer.phone != phone:
        customer.phone = phone
        customer_updated = True

    if customer_updated:
        if created:
            customer.save()
        else:
            customer.save(update_fields=['name', 'phone'])

    return customer

@role_required(User.EMPLOYEE)
def edit_customer(request, id):

    customer = get_object_or_404(
        Customer,
        id=id
    )

    if request.method == 'POST':

        customer.name = request.POST.get('name')
        customer.phone = request.POST.get('phone')
        customer.email = request.POST.get('email')
        customer.save(update_fields=['name', 'phone', 'email'])

        messages.success(
            request,
            'Customer updated successfully.'
        )

        return redirect('customers')

    context = {
        'customer': customer
    }

    return render(request, 'dashboard/edit_customer.html', context)

@role_required(User.EMPLOYEE)
def delete_customer(request, customer_id):
    customer = get_object_or_404(Customer, id=customer_id)

    if request.method == "POST":
        customer.delete()
        messages.success(request, "Customer deleted successfully.")
        return redirect('customers')  

    return render(request, 'dashboard/confirm_delete.html', {'customer': customer})

# SALES CRUD VIEWS

@role_required(User.CASHIER)
def add_sale(request):
    if request.method == 'POST':
        customer_name = (request.POST.get('customer_name') or '').strip()
        phone = (request.POST.get('phone_number') or '').strip()
        email = (request.POST.get('email') or '').strip().lower()
        product_id = request.POST.get('product')

        try:
            quantity = int(request.POST.get('quantity'))
            price = float(request.POST.get('price'))
        except (TypeError, ValueError):
            messages.error(request, "Enter a valid quantity and price.")
            return redirect('add_sale')

        if not customer_name or not email or not product_id:
            messages.error(request, "Customer, email, and product are required.")
            return redirect('add_sale')

        customer = upsert_customer(customer_name, phone, email)
        product = get_object_or_404(Product, id=product_id )

        stock_error = validate_stock_movement(product, quantity, StockMovement.MOVEMENT_OUT)
        if stock_error:
            messages.error(request, stock_error)
            return redirect('add_sale')

        with transaction.atomic():
            sale = Sales.objects.create(
                customer=customer,
                product=product,
                quantity=quantity,
                price=price,
            )
            create_stock_movement(
                product=product,
                quantity=quantity,
                movement_type=StockMovement.MOVEMENT_OUT,
                note=f"Sale #{sale.id} recorded.",
            )

        messages.success(request, "Sale added successfully.")
        return redirect('sales')

    products = Product.objects.all()
    return render(request, 'dashboard/add_sale.html', {'products': products})


@role_required(User.CASHIER)
def edit_sale(request, sale_id):
    sale = get_object_or_404(Sales.objects.select_related('customer', 'product'), id=sale_id)

    if request.method == 'POST':
        customer_name = (request.POST.get('customer_name') or '').strip()
        phone = (request.POST.get('phone_number') or '').strip()
        email = (request.POST.get('email') or '').strip().lower()
        product_id = request.POST.get('product')

        try:
            quantity = int(request.POST.get('quantity'))
            price = float(request.POST.get('price'))
        except (TypeError, ValueError):
            messages.error(request, "Enter a valid quantity and price.")
            return redirect('edit_sale', sale_id=sale.id)

        if not customer_name or not email or not product_id:
            messages.error(request, "Customer, email, and product are required.")
            return redirect('edit_sale', sale_id=sale.id)

        updated_product = get_object_or_404(Product, id=product_id)
        customer = upsert_customer(customer_name, phone, email, current_customer=sale.customer)

        try:
            with transaction.atomic():
                create_stock_movement(
                    product=sale.product,
                    quantity=sale.quantity,
                    movement_type=StockMovement.MOVEMENT_IN,
                    note=f"Sale #{sale.id} update reversal.",
                )
                create_stock_movement(
                    product=updated_product,
                    quantity=quantity,
                    movement_type=StockMovement.MOVEMENT_OUT,
                    note=f"Sale #{sale.id} updated.",
                )

                sale.customer = customer
                sale.product = updated_product
                sale.quantity = quantity
                sale.price = price
                sale.save(update_fields=['customer', 'product', 'quantity', 'price'])
        except ValueError as exc:
            messages.error(request, str(exc))
            return redirect('edit_sale', sale_id=sale.id)

        messages.success(request, "Sale updated successfully.")
        return redirect('sales')

    products = Product.objects.all()
    context = {
        'sale': sale,
        'products': products,
    }
    return render(request, 'dashboard/edit_sale.html', context)


@role_required(User.CASHIER)
def delete_sale(request, sale_id):
    sale = get_object_or_404(Sales, id=sale_id)

    if request.method == 'POST':
        with transaction.atomic():
            create_stock_movement(
                product=sale.product,
                quantity=sale.quantity,
                movement_type=StockMovement.MOVEMENT_IN,
                note=f"Sale #{sale.id} deleted.",
            )
            sale.delete()
        messages.success(request, "Sale deleted successfully.")
        return redirect('sales')

    messages.error(request, "Invalid request method for deleting a sale.")
    return redirect('sales')


# REPORTS VIEW

@role_required(User.MANAGER)
def reports(request):
    start_date_raw = (request.GET.get('start_date') or '').strip()
    end_date_raw = (request.GET.get('end_date') or '').strip()
    export_format = (request.GET.get('export') or '').strip().lower()

    start_date = parse_date(start_date_raw) if start_date_raw else None
    end_date = parse_date(end_date_raw) if end_date_raw else None

    sales = Sales.objects.select_related('customer', 'product').order_by('-created_at')
    payments = Payment.objects.select_related('sale', 'business').order_by('-payment_date')
    expenses = Expense.objects.order_by('-date')

    if start_date:
        sales = sales.filter(created_at__date__gte=start_date)
        payments = payments.filter(payment_date__date__gte=start_date)
        expenses = expenses.filter(date__gte=start_date)

    if end_date:
        sales = sales.filter(created_at__date__lte=end_date)
        payments = payments.filter(payment_date__date__lte=end_date)
        expenses = expenses.filter(date__lte=end_date)

    total_revenue = payments.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    total_expenses = expenses.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    net_result = total_revenue - total_expenses
    profit = net_result if net_result > 0 else Decimal('0.00')
    loss = abs(net_result) if net_result < 0 else Decimal('0.00')
    total_sales_count = sales.count()
    total_payments_logged = payments.count()

    if export_format == 'csv':
        response = HttpResponse(content_type='text/csv')
        filename_bits = ['smartbiz-report']
        if start_date_raw:
            filename_bits.append(start_date_raw)
        if end_date_raw:
            filename_bits.append(end_date_raw)
        response['Content-Disposition'] = f'attachment; filename="{"-".join(filename_bits)}.csv"'

        writer = csv.writer(response)
        writer.writerow(['SmartBiz Report'])
        writer.writerow(['Start Date', start_date_raw or 'All'])
        writer.writerow(['End Date', end_date_raw or 'All'])
        writer.writerow(['Total Revenue', total_revenue])
        writer.writerow(['Total Expenses', total_expenses])
        writer.writerow(['Profit', profit])
        writer.writerow(['Loss', loss])
        writer.writerow(['Sales Count', total_sales_count])
        writer.writerow(['Payments Logged', total_payments_logged])
        writer.writerow([])
        writer.writerow(['Customer', 'Product', 'Quantity', 'Unit Price', 'Amount', 'Date'])

        for sale in sales:
            writer.writerow([
                sale.customer.name,
                sale.product.name,
                sale.quantity,
                sale.price,
                sale.total_amount,
                sale.created_at.strftime('%Y-%m-%d %H:%M'),
            ])

        return response

    context = {
        'sales': sales,
        'total_revenue': total_revenue,
        'total_expenses': total_expenses,
        'profit': profit,
        'loss': loss,
        'total_sales_count': total_sales_count,
        'total_payments_logged': total_payments_logged,
        'start_date': start_date_raw,
        'end_date': end_date_raw,
    }

    return render(request, 'dashboard/report.html', context)


# PASSWORD RESET VIEW


def custom_password_reset(request):
    if request.method == 'POST':
        form = PasswordResetForm(request.POST)

        if form.is_valid():
            form.save(
                request=request,
                email_template_name='dashboard/password_reset_email.html',
                subject_template_name='dashboard/password_reset_subject.txt',
            )
            return redirect('password_reset_done')
    else:
        form = PasswordResetForm()

    return render(request, 'dashboard/password_reset.html', {'form': form})

# PRODUCT VIEW
@role_required(User.EMPLOYEE)
def product_list(request):
    products = Product.objects.all().order_by('-created_at')
    low_stock_count = Product.objects.filter(stock_quantity__lte=F('low_stock_threshold')).count()
    out_of_stock_count = Product.objects.filter(stock_quantity__lte=0).count()
    return render(request, 'dashboard/product_list.html', {
        'products': products,
        'low_stock_count': low_stock_count,
        'out_of_stock_count': out_of_stock_count,
    })

@role_required(User.MANAGER)
def add_product(request):
    if request.method == 'POST':
        form = ProductForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('product_list')
    else:
        form = ProductForm()
    return render(request, 'dashboard/add_product.html', {'form': form})

@role_required(User.MANAGER)
def edit_product(request, pk):
    product = get_object_or_404(Product, pk=pk)
    form = ProductForm(request.POST or None, instance=product)
    if form.is_valid():
        form.save()
        return redirect('product_list')
    return render(request, 'dashboard/edit_product.html', {'form': form})

@role_required(User.MANAGER)
def delete_product(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        product.delete()
        messages.success(request, "Product deleted successfully.")
        return redirect('product_list')

    return render(request, 'dashboard/confirm_delete.html', {'product': product})

# stock movement
@role_required(User.EMPLOYEE)
def stock_view(request):
    if request.method == 'POST':
        form = StockMovementForm(request.POST)
        if form.is_valid():
            movement = form.save(commit=False)
            try:
                create_stock_movement(
                    product=movement.product,
                    quantity=movement.quantity,
                    movement_type=movement.movement_type,
                    note=movement.note,
                )
            except ValueError as exc:
                messages.error(request, str(exc))
            else:
                action = 'added to' if movement.movement_type == StockMovement.MOVEMENT_IN else 'removed from'
                messages.success(
                    request,
                    f"{movement.quantity} units {action} {movement.product.name}. Current stock: {movement.product.stock_quantity}."
                )
                return redirect('Stock_movement')
    else:
        form = StockMovementForm()

    movements = StockMovement.objects.select_related('product').order_by('-date')
    low_stock_products = Product.objects.filter(stock_quantity__lte=F('low_stock_threshold')).order_by('stock_quantity', 'name')
    unread_alerts = models.StockAlert.objects.select_related('product').filter(is_read=False).order_by('-created_at')[:10]
    context = {
         'movements': movements,
         'form': form,
         'low_stock_products': low_stock_products,
         'unread_alerts': unread_alerts,
     }
 
    return render(request,'dashboard/stock_movement.html',context)
