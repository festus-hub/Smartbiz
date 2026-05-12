from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from dashboard.models import Product, Sales, User

# Register your models here.
@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    list_display = ('username', 'email', 'first_name', 'role', 'is_staff', 'is_superuser')
    list_filter = ('role', 'is_staff', 'is_superuser', 'is_active')
    fieldsets = DjangoUserAdmin.fieldsets + (
        ('SmartBiz Access', {'fields': ('role',)}),
    )

admin.site.register(Product)
admin.site.register(Sales)
