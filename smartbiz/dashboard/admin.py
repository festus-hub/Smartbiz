from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from dashboard.models import ContactMessage, Product, Sales, User, StockMovement

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
admin.site.register(StockMovement)


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'subject', 'is_read', 'created_at')
    list_filter = ('is_read', 'created_at')
    search_fields = ('name', 'email', 'subject', 'message')
