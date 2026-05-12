from django import forms
from .models import Sales,Customer,Product


class SalesForm(forms.ModelForm):
    class Meta:
        model = Sales
        fields = ['customer', 'product', 'quantity', 'price']

class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = ['name', 'email', 'phone']

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'category', 'price', 'price', 'stock_quantity' ]

