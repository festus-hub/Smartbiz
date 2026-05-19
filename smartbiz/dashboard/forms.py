from django import forms
from .models import Sales, Customer, Product, StockMovement


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
        fields = ['name', 'category', 'price', 'stock_quantity', 'low_stock_threshold']


class StockMovementForm(forms.ModelForm):
    class Meta:
        model = StockMovement
        fields = ['product', 'movement_type', 'quantity', 'note']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['quantity'].min_value = 1
        self.fields['note'].required = False

