# admin.py
from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from posApp.models import Category, Products, Sales, salesItems, Employee, Department, Position, UserRole

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