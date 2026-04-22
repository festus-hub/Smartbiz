from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('staff', 'Staff'),
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='staff')


    def __str__(self):
           return f"{self.username} ({self.role})"

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
              return f"sale #{self.id} - {self.price}"
        
        def calculate_total(self):
              total = sum(item.subtotal() for item in self.saleitem_set.all())
              self.total_amount = total
              self.save()
              return total

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
        payment_date = models.DateTimeField(auto_now_add=True)
        phone_number = models.CharField(max_length=20, blank=True, null=True)

        def __str__(self):
              return f"{self.payment_method} - {self.amount}"
        

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