from datetime import datetime
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.db.models import Sum
from .models import Sales, Payment, Customer, User, Product, Expense
from . import models

def landing_page(request):
    return render(request, 'dashboard/landing.html')

def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect('dashboard') 
        else:
            messages.error(request, "Invalid username or password")
            return redirect('register')

    return render(request, 'dashboard/login.html')

def logout_view(request):
    logout(request)
    return redirect('landing')


def register_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')

        #Tomorrow make sure we have gone through this.

        if password != confirm_password:
            messages.error(request, "Passwords do not match")
            return redirect('register')

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists")
            return redirect('register')

        user = User.objects.create_user(username=username, email=email, password=password)
        user.save()

        messages.success(request, "Account created successfully. Please login.")
        return redirect('login')   

    return render(request, 'dashboard/register.html')

@login_required(login_url='login')
def dashboard(request):
    total_sales = Sales.objects.count()
    total_customers = Customer.objects.count()
    total_products = Product.objects.count()

    total_revenue = Payment.objects.filter(amount__isnull=False).aggregate(
        total=Sum('amount') )['total'] or 0
      

    total_expenses = Expense.objects.aggregate(
        total=Sum('amount')
    )['total'] or 0

    profit = total_revenue - total_expenses

    monthly_sales = [0] * 12
    monthly_revenue = [0] * 12
    monthly_expenses = [0] * 12

    sales = Sales.objects.all()
    payments = Payment.objects.all()
    expenses = Expense.objects.all()

    for sale in sales:
        month = sale.created_at.month - 1
        monthly_sales[month] += 1

    for pay in payments:
        month = pay.payment_date.month - 1
        monthly_revenue[month] += float(pay.amount)

    for exp in expenses:
        month = exp.date.month - 1
        monthly_expenses[month] += float(exp.amount)

    recent_sales = Sales.objects.order_by('-created_at')[:5]

    # Pending payments: sales with no associated payment
    pending_payments = Sales.objects.filter(payments__isnull=True).count()
    context = {
        'total_sales': total_sales,
        'total_customers': total_customers,
        'total_products': total_products,
        'total_revenue': total_revenue,
        'total_expenses': total_expenses,
        'profit': profit,
        'monthly_sales': monthly_sales,
        'monthly_revenue': monthly_revenue,
        'monthly_expenses': monthly_expenses,
        'recent_sales': recent_sales,
        'pending_payments': pending_payments,
    }

    return render(request, 'dashboard/index.html', context)

def payments_view(request):
    payments = Payment.objects.order_by('-payment_date')
    context = {
        'payments': payments,
    }
    return render(request, 'dashboard/payment.html', context)

def sales_view(request):
    sales = Sales.objects.order_by('-created_at')
    total_sales = Sales.objects.count()
    total_revenue = Payment.objects.aggregate(total=Sum('amount'))['total'] or 0

    context = {
        'sales': sales,
        'total_sales': total_sales,
        'total_revenue': total_revenue,
    }
    return render(request, 'dashboard/sales.html', context)

def customers_view(request):
    customers = models.Customer.objects.order_by('-created_at')
    return render(request, 'dashboard/customer.html', {'customers': customers})

def add_sale(request):
    if request.method == 'POST':
        customer_name = request.POST.get('customer_name')
        phone = request.POST.get('phone_number')
        email = request.POST.get('email')
        product_id = request.POST.get('product')
        quantity = int(request.POST.get('quantity'))
        price = float(request.POST.get('price'))
        sales = Sales.objects.all()

        customer, created = Customer.objects.get_or_create(
            name=customer_name,
            phone=phone,
            email=email
        )

        if not created:
            customer.phone = phone
            customer.email = email
            customer.save()

        product = Product.objects.get(id=product_id)

        sales = Sales.objects.create(
            customer=customer,
            product=product,
            quantity=quantity,
            price=price
        )

        messages.success(request, "Sale added successfully.")
        return redirect('sales')

    products = Product.objects.all()
    return render(request, 'dashboard/add_sale.html', {'products': products})


