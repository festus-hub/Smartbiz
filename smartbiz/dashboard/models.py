from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    SUPER_ADMIN = 'super_admin'
    BUSINESS_OWNER = 'business_owner'
    MANAGER = 'manager'
    CASHIER = 'cashier'
    EMPLOYEE = 'employee'

    ROLE_CHOICES = (
        (SUPER_ADMIN, 'Super Admin'),
        (BUSINESS_OWNER, 'Business Owner'),
        (MANAGER, 'Manager'),
        (CASHIER, 'Cashier'),
        (EMPLOYEE, 'Employee'),
    )
    ROLE_HIERARCHY = {
        EMPLOYEE: 1,
        CASHIER: 2,
        MANAGER: 3,
        BUSINESS_OWNER: 4,
        SUPER_ADMIN: 5,
    }
    LEGACY_ROLE_MAP = {
        'admin': BUSINESS_OWNER,
        'staff': EMPLOYEE,
    }
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=EMPLOYEE)

    @property
    def effective_role(self):
        if self.is_superuser:
            return self.SUPER_ADMIN
        return self.LEGACY_ROLE_MAP.get(self.role, self.role)

    @property
    def role_label(self):
        return dict(self.ROLE_CHOICES).get(self.effective_role, 'Employee')

    def role_level(self):
        return self.ROLE_HIERARCHY.get(self.effective_role, 0)

    def has_minimum_role(self, minimum_role):
        if self.is_superuser:
            return True
        return self.role_level() >= self.ROLE_HIERARCHY.get(minimum_role, 0)


    def __str__(self):
           return f"{self.username} ({self.effective_role})"
class Expense(models.Model):
    CATEGORY_CHOICES = (
        ('operational', 'Operational'),
        ('salary', 'Salary'),
        ('marketing', 'Marketing'),
        ('other', 'Other'),
    )
    description = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='other')
    date = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"{self.description} - {self.amount}"

class Business(models.Model):
        name = models.CharField(max_length=255)
        owner = models.ForeignKey(User, on_delete=models.CASCADE)
        created_at = models.DateTimeField(auto_now_add=True)

        def __str__(self):
            return self.name

class Customer(models.Model):
        name = models.CharField(max_length=150)
        email = models.EmailField(unique=True)
        phone = models.CharField(max_length=20,blank=True)
        created_at = models.DateTimeField(auto_now_add=True)

        def __str__(self):
           return self.name

class Product(models.Model):
        CATEGORY_CHOICES = (
            ('electronics', 'Electronics'),
            ('accessories', 'Accessories'),
            ('mobile', 'Mobile Devices'),
            ('office', 'Office Supplies'),
            ('services', 'Services'),)
        
        name = models.CharField(max_length=150)
        category = models.CharField(max_length=100)
        price = models.DecimalField(max_digits=10, decimal_places=2)
        stock_quantity = models.IntegerField()
        created_at = models.DateTimeField(auto_now_add=True)

        def __str__(self):
           return self.name


class Sales(models.Model):
        customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
        product = models.ForeignKey(Product, on_delete=models.CASCADE)
        quantity = models.IntegerField()
        price = models.DecimalField(max_digits=10, decimal_places=2)
        created_at = models.DateTimeField(auto_now_add=True)

        def __str__(self):
              return f"sale #{self.id} - {self.total_amount}"

        @property
        def total_amount(self):
              return self.quantity * self.price
        
        def calculate_total(self):
              return self.total_amount

class SaleItem(models.Model):
        sale = models.ForeignKey(Sales, on_delete=models.CASCADE)
        product = models.ForeignKey(Product, on_delete=models.CASCADE)
        quantity = models.IntegerField()
        price = models.DecimalField(max_digits=10, decimal_places=2)

        def subtotal(self):
              return self.quantity * self.price
        
        def __str__(self):
              return f"{self.product.name} x {self.quantity}"

class Payment(models.Model):
        STATUS_PENDING = 'pending'
        STATUS_SUCCESS = 'success'
        STATUS_FAILED = 'failed'
        STATUS_CHOICES = (
            (STATUS_PENDING, 'Pending'),
            (STATUS_SUCCESS, 'Success'),
            (STATUS_FAILED, 'Failed'),
        )
        PAYMENT_METHODS = (
            ('cash', 'Cash'),
            ('card', 'Card'),
            ('mpesa', 'M-Pesa'),
        )
        sale = models.ForeignKey(Sales, on_delete=models.CASCADE, related_name='payments')
        business = models.ForeignKey(Business, on_delete=models.CASCADE)
        amount = models.DecimalField(max_digits=10, decimal_places=2)
        payment_method = models.CharField(max_length=50)
        transaction_id = models.CharField(max_length=100, blank=True, null=True)
        merchant_request_id = models.CharField(max_length=100, blank=True, null=True)
        checkout_request_id = models.CharField(max_length=100, blank=True, null=True)
        status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
        result_code = models.CharField(max_length=20, blank=True, null=True)
        result_description = models.TextField(blank=True, null=True)
        callback_payload = models.JSONField(blank=True, null=True)
        payment_date = models.DateTimeField(auto_now_add=True)
        phone_number = models.CharField(max_length=20, blank=True, null=True)

        def __str__(self):
              return f"{self.payment_method} - {self.amount} ({self.status})"
        

class Analytics(models.Model):
        date = models.DateField()
        business = models.ForeignKey(Business, on_delete=models.CASCADE)
        total_sales = models.DecimalField(max_digits=10, decimal_places=2, default=0)
        total_customers = models.IntegerField(default=0)

        def __str__(self):
              return f"{self.business.name} - {self.date}"


class StockMovement(models.Model):
        MOVEMENT_TYPES = (
            ('in', 'Stock In'),
            ('out', 'Stock Out'),
        )
        product = models.ForeignKey(Product, on_delete=models.CASCADE)
        quantity = models.IntegerField()
        movement_type = models.CharField(max_length=10)  # 'in' or 'out'
        date = models.DateTimeField(auto_now_add=True)

        def __str__(self):
              return f"{self.product.name} - {self.movement_type} - {self.quantity}"
