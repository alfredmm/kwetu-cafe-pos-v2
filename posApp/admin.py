# admin.py
from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from posApp.models import Category, Products, Sales, salesItems, Employee, Department, Position, UserRole
from django.utils.html import format_html
from .models import MpesaTransaction

class UserRoleInline(admin.StackedInline):
    model = UserRole
    can_delete = False

class EmployeeInline(admin.StackedInline):
    model = Employee
    can_delete = False

class UserAdmin(BaseUserAdmin):
    inlines = (UserRoleInline, EmployeeInline)
    
    def get_inline_instances(self, request, obj=None):
        if not obj:
            return list()
        return super().get_inline_instances(request, obj)
class MpesaTransactionAdmin(admin.ModelAdmin):
    list_display = ('phone_number','customer_name', 'amount', 'colored_status', 'transaction_date', 'receipt_number')
    list_filter = ('status', 'transaction_date')
    search_fields = ('phone_number', 'checkout_request_id', 'receipt_number')
    #readonly_fields = ('merchant_request_id', 'checkout_request_id', 'raw_response', 'transaction_date')

    def colored_status(self, obj):
        if obj.status == 'Completed':
            color = 'green'
        elif obj.status == 'Failed':
            color = 'red'
        else: # For 'Pending' or other statuses
            color = 'orange'
        return format_html('<span style="color: {};">{}</span>', color, obj.status)
    
    colored_status.short_description = 'Status' # Sets the column header name in the admin list

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ['code', 'firstname', 'lastname', 'email', 'department', 'position', 'status', 'date_hired']
    list_filter = ['status', 'department', 'position', 'gender', 'date_hired']
    search_fields = ['code', 'firstname', 'lastname', 'email']
    readonly_fields = ['code', 'date_added', 'date_updated']
    
    fieldsets = (
        ('Personal Information', {
            'fields': ('code', 'firstname', 'middlename', 'lastname', 'gender', 'dob', 'email')
        }),
        ('Contact Information', {
            'fields': ('contact', 'address')
        }),
        ('Employment Details', {
            'fields': ('user', 'department', 'position', 'date_hired', 'salary', 'status')
        }),
        ('System Information', {
            'fields': ('date_added', 'date_updated'),
            'classes': ('collapse',)
        }),
    )

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ['name', 'description', 'date_added']
    search_fields = ['name']

@admin.register(Position)
class PositionAdmin(admin.ModelAdmin):
    list_display = ['name', 'description', 'date_added']
    search_fields = ['name']

@admin.register(UserRole)
class UserRoleAdmin(admin.ModelAdmin):
    list_display = ['user', 'role', 'is_active', 'date_created']
    list_filter = ['role', 'is_active']
    search_fields = ['user__username', 'user__email']

# Re-register UserAdmin
admin.site.unregister(User)
admin.site.register(User, UserAdmin)

# Register your original models
admin.site.register(Category)
admin.site.register(Products)
admin.site.register(Sales)
admin.site.register(salesItems)
admin.site.register(MpesaTransaction, MpesaTransactionAdmin)