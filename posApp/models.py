from datetime import datetime
from unicodedata import category
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
import string
import random

# Create your models here.

# class Employees(models.Model):
#     code = models.CharField(max_length=100,blank=True) 
#     firstname = models.TextField() 
#     middlename = models.TextField(blank=True,null= True) 
#     lastname = models.TextField() 
#     gender = models.TextField(blank=True,null= True) 
#     dob = models.DateField(blank=True,null= True) 
#     contact = models.TextField() 
#     address = models.TextField() 
#     email = models.TextField() 
#     department_id = models.ForeignKey(Department, on_delete=models.CASCADE) 
#     position_id = models.ForeignKey(Position, on_delete=models.CASCADE) 
#     date_hired = models.DateField() 
#     salary = models.FloatField(default=0) 
#     status = models.IntegerField() 
#     date_added = models.DateTimeField(default=timezone.now) 
#     date_updated = models.DateTimeField(auto_now=True) 

    # def __str__(self):
    #     return self.firstname + ' ' +self.middlename + ' '+self.lastname + ' '
class Category(models.Model):
    name = models.TextField()
    description = models.TextField()
    status = models.IntegerField(default=1) 
    date_added = models.DateTimeField(default=timezone.now) 
    date_updated = models.DateTimeField(auto_now=True) 

    def __str__(self):
        return self.name
class Products(models.Model):
    code = models.CharField(max_length=100, unique=True, blank=True)
    category_id = models.ForeignKey(Category, on_delete=models.CASCADE)
    name = models.TextField()
    description = models.TextField()
    price = models.FloatField(default=0)
    status = models.IntegerField(default=1) 
    date_added = models.DateTimeField(default=timezone.now) 
    date_updated = models.DateTimeField(auto_now=True) 
    
    def generate_unique_code(self):
        """Generate a unique product code"""
        while True:
            # Option 1: Sequential format (PROD-0001, PROD-0002, etc.)
            last_product = Products.objects.order_by('-id').first()
            if last_product and last_product.code.startswith('PROD-'):
                try:
                    last_number = int(last_product.code.split('-')[-1])
                    next_number = last_number + 1
                except (ValueError, IndexError):
                    next_number = 1
            else:
                next_number = 1
            
            code = f"PROD-{next_number:04d}"
            
            # Check if code already exists
            if not Products.objects.filter(code=code).exists():
                return code
            
            # If somehow the sequential code exists, add random suffix
            random_suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=2))
            code = f"PROD-{next_number:04d}-{random_suffix}"
            if not Products.objects.filter(code=code).exists():
                return code
    
    def save(self, *args, **kwargs):
        # Generate code only for new products (no existing code)
        if not self.code:
            self.code = self.generate_unique_code()
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.code + " - " + self.name

    class Meta:
        verbose_name = "Product"
        verbose_name_plural = "Products"

class Sales(models.Model):
    code = models.CharField(max_length=100)
    sub_total = models.FloatField(default=0)
    grand_total = models.FloatField(default=0)
    tax_amount = models.FloatField(default=0)
    tax = models.FloatField(default=0)
    tendered_amount = models.FloatField(default=0)
    amount_change = models.FloatField(default=0)
    date_added = models.DateTimeField(default=timezone.now) 
    date_updated = models.DateTimeField(auto_now=True) 

    def __str__(self):
        return self.code

class salesItems(models.Model):
    sale_id = models.ForeignKey(Sales,on_delete=models.CASCADE)
    product_id = models.ForeignKey(Products,on_delete=models.CASCADE)
    price = models.FloatField(default=0)
    qty = models.FloatField(default=0)
    total = models.FloatField(default=0)

class Department(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    date_added = models.DateTimeField(default=timezone.now)
    date_updated = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name

class Position(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    date_added = models.DateTimeField(default=timezone.now)
    date_updated = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name

class UserRole(models.Model):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('manager', 'Manager'),
        ('waiter', 'Waiter'),
        ('cashier', 'Cashier'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='waiter')
    is_active = models.BooleanField(default=True)
    date_created = models.DateTimeField(default=timezone.now)
    
    def __str__(self):
        return f"{self.user.username} - {self.role}"

class Employee(models.Model):
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
    ]
    
    STATUS_CHOICES = [
        (1, 'Active'),
        (0, 'Inactive'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    code = models.CharField(max_length=100, blank=True, unique=True)
    firstname = models.CharField(max_length=100)
    middlename = models.CharField(max_length=100, blank=True, null=True)
    lastname = models.CharField(max_length=100)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True, null=True)
    dob = models.DateField(blank=True, null=True)
    contact = models.CharField(max_length=20)
    address = models.TextField()
    email = models.EmailField()
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    position = models.ForeignKey(Position, on_delete=models.CASCADE)
    date_hired = models.DateField()
    salary = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.IntegerField(choices=STATUS_CHOICES, default=1)
    date_added = models.DateTimeField(default=timezone.now)
    date_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        middle = f" {self.middlename}" if self.middlename else ""
        return f"{self.firstname}{middle} {self.lastname}"
    
    def save(self, *args, **kwargs):
        if not self.code:
            # Generate employee code automatically
            last_employee = Employee.objects.all().order_by('id').last()
            if last_employee:
                emp_id = last_employee.id + 1
            else:
                emp_id = 1
            self.code = f"EMP{emp_id:04d}"
        super().save(*args, **kwargs)
    

    class Meta:
        ordering = ['firstname', 'lastname']

class MpesaTransaction(models.Model):
    merchant_request_id = models.CharField(max_length=100, unique=True)
    checkout_request_id = models.CharField(max_length=100, unique=True)
    customer_name = models.CharField(max_length=100, blank=True, null=True)
    phone_number = models.CharField(max_length=15)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    receipt_number = models.CharField(max_length=100, blank=True, null=True)
    transaction_date = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, default='')
    raw_response = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.phone_number} - {self.amount} - {self.status} - {self.transaction_date}"
    
