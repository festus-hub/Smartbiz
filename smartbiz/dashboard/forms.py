from django import forms
from .models import Sales, Customer, Product, StockMovement, ContactMessage


TAILWIND_FIELD_CLASS = (
    "form-control rounded-4 border-slate-300 bg-white px-4 py-3 text-slate-900 "
    "shadow-sm transition focus:border-blue-600 focus:ring-4 focus:ring-blue-600/10"
)

TAILWIND_SELECT_CLASS = (
    "form-select rounded-4 border-slate-300 bg-white px-4 py-3 text-slate-900 "
    "shadow-sm transition focus:border-blue-600 focus:ring-4 focus:ring-blue-600/10"
)

TAILWIND_TEXTAREA_CLASS = (
    "form-control rounded-4 border-slate-300 bg-white px-4 py-3 text-slate-900 "
    "shadow-sm transition focus:border-blue-600 focus:ring-4 focus:ring-blue-600/10"
)


def apply_tailwind_field_styles(field):
    widget = field.widget

    if isinstance(widget, (forms.CheckboxInput, forms.RadioSelect)):
        return

    if isinstance(widget, (forms.Select, forms.SelectMultiple)):
        widget.attrs["class"] = TAILWIND_SELECT_CLASS
    elif isinstance(widget, forms.Textarea):
        widget.attrs["class"] = TAILWIND_TEXTAREA_CLASS
    else:
        widget.attrs["class"] = TAILWIND_FIELD_CLASS


class SalesForm(forms.ModelForm):
    class Meta:
        model = Sales
        fields = ['customer', 'product', 'quantity', 'price']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            apply_tailwind_field_styles(field)

class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = ['name', 'email', 'phone']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            apply_tailwind_field_styles(field)

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'category', 'price', 'stock_quantity', 'low_stock_threshold']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            apply_tailwind_field_styles(field)


class StockMovementForm(forms.ModelForm):
    class Meta:
        model = StockMovement
        fields = ['product', 'movement_type', 'quantity', 'note']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['quantity'].min_value = 1
        self.fields['note'].required = False
        for field in self.fields.values():
            apply_tailwind_field_styles(field)


class ContactMessageForm(forms.ModelForm):
    class Meta:
        model = ContactMessage
        fields = ['name', 'email', 'subject', 'message']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            apply_tailwind_field_styles(field)

