from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse, HttpResponseBadRequest
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.http import require_POST
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.views.decorators.csrf import csrf_exempt
from django.core.paginator import Paginator
from posApp.models import Category, Products, Sales, salesItems, Employee, Department, Position, UserRole
from posApp.forms import EmployeeForm, UserRoleForm
import json, sys
from datetime import date, datetime, timedelta
from django.db.models import Count, Sum, F
import calendar
from django.db.models.functions import TruncDay, ExtractDay
from collections import defaultdict
from .forms import UserForm


# This works when forms.py is in the same app

# Authentication and Role Management Functions
def is_admin_or_manager(user):
    """Check if user is admin or manager"""
    if not user.is_authenticated:
        return  False
    if user.is_superuser:
        return True
    try:
        user_role = UserRole.objects.get(user=user)
        return user_role.role in ['admin', 'manager']
    except UserRole.DoesNotExist:
        return False

# def get_user_role(user):
#     """Get user role"""
#     if user.is_superuser:
#         return 'admin'
#     try:
#         user_role = UserRole.objects.get(user=user)
#         return user_role.role
#     except UserRole.DoesNotExist:
#         return 'waiter'  # default role

# # Context processor for global template variables
# def user_role_context(request):
#     """Add user role to all templates"""
#     if request.user.is_authenticated:
#         user_role = get_user_role(request.user)
#         return {
#             'user_role': user_role,
#             'show_admin_menu': user_role in ['admin', 'manager'],
#             'show_pos_only': user_role == 'waiter',
#         }
#     return {}

# Authentication Views
def login_user(request):
    logout(request)
    resp = {"status":'failed','msg':''}
    username = ''
    password = ''
    if request.POST:
        username = request.POST['username']
        password = request.POST['password']

        user = authenticate(username=username, password=password)
        if user is not None:
            if user.is_active:
                login(request, user)
                resp['status']='success'
            else:
                resp['msg'] = "Incorrect username or password"
        else:
            resp['msg'] = "Incorrect username or password"
    return HttpResponse(json.dumps(resp),content_type='application/json')

def logoutuser(request):
    logout(request)
    return redirect('/')

# Dashboard Views
@login_required
def home(request):
    """Main dashboard with role-based content"""
    user_role = get_user_role(request.user)
    
    if user_role == 'waiter':
        return redirect('pos')
    
    now = datetime.now()
    current_year = now.strftime("%Y")
    current_month = now.strftime("%m")
    current_day = now.strftime("%d")
    
    # Basic dashboard stats (original home view data)
    categories = len(Category.objects.all())
    products = len(Products.objects.all())
    transaction = len(Sales.objects.filter(
        date_added__year=current_year,
        date_added__month=current_month,
        date_added__day=current_day
    ))
    
    today_sales = Sales.objects.filter(
        date_added__year=current_year,
        date_added__month=current_month,
        date_added__day=current_day
    ).all()
    
    total_sales_today = sum(today_sales.values_list('grand_total', flat=True))
    
    # Additional monthly analytics for charts
    year = int(request.GET.get('year', now.year))
    month = int(request.GET.get('month', now.month))
    days_in_month = calendar.monthrange(year, month)[1]
    
    # Monthly sales data
    month_sales = Sales.objects.filter(
        date_added__year=year,
        date_added__month=month
    )
    
    total_month_sales = month_sales.aggregate(Sum('grand_total'))['grand_total__sum'] or 0
    
    # Daily sales for chart
    daily_sales = month_sales.annotate(
        day=ExtractDay('date_added')
    ).values('day').annotate(
        total=Sum('grand_total')
    ).order_by('day')
    
    daily_sales_dict = {item['day']: float(item['total']) for item in daily_sales}
    daily_sales_data = []
    for day in range(1, days_in_month + 1):
        daily_sales_data.append({
            'day': str(day),
            'total': daily_sales_dict.get(day, 0)
        })
    
    # Top selling products this month
    top_products = salesItems.objects.filter(
        sale_id__date_added__year=year,
        sale_id__date_added__month=month
    ).values(
        'product_id',
        'product_id__name'
    ).annotate(
        qty_sum=Sum('qty'),
        total_sum=Sum('total')
    ).order_by('-qty_sum')[:10]
    
    # Category sales distribution
    category_sales = salesItems.objects.filter(
        sale_id__date_added__year=year,
        sale_id__date_added__month=month
    ).values(
        'product_id__category_id',
        'product_id__category_id__name'
    ).annotate(
        count=Sum('qty')
    ).order_by('-count')
    
    # Filter out None categories
    category_sales_data = [
        {
            'name': category['product_id__category_id__name'],
            'count': int(category['count'])
        }
        for category in category_sales 
        if category['product_id__category_id__name']
    ]
    
    context = {
        'page_title': 'Dashboard',
        'user_role': user_role,
        'show_admin_menu': user_role in ['admin', 'manager'],
        'show_pos_only': user_role == 'waiter',
        # Original home view data
        'categories': categories,
        'products': products,
        'transaction': transaction,
        'total_sales': total_sales_today,
        # Chart data
        'current_year': year,
        'current_month': month,
        'total_month_sales': total_month_sales,
        'daily_sales_data': daily_sales_data,
        'top_products': top_products,
        'category_sales_data': category_sales_data,
        'days_in_month': days_in_month,
    }
    
    if user_role in ['admin', 'manager']:
        # Admin/Manager dashboard stats
        context.update({
            'total_employees': Employee.objects.filter(status=1).count(),
            'total_users': User.objects.filter(is_active=True).count(),
            'total_departments': Department.objects.count(),
            'total_positions': Position.objects.count(),
        })
    
    return render(request, 'posApp/home.html', context)

def user_list(request):
    """List all users with pagination and search functionality"""
    search_query = request.GET.get('search', '')
    
    # Base queryset
    users = User.objects.all().order_by('-date_joined')
    
    # Apply search filter if provided
    if search_query:
        users = users.filter(
            username__icontains=search_query
        ) | users.filter(
            email__icontains=search_query
        ) | users.filter(
            first_name__icontains=search_query
        ) | users.filter(
            last_name__icontains=search_query
        )
    
    # Pagination
    paginator = Paginator(users, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'active_users': User.objects.filter(is_active=True).count(),
        'staff_users': User.objects.filter(is_staff=True).count(),
    }
    return render(request, 'posApp/user_list_test.html', context)

@login_required
def user_create(request):
    """Handle user creation via modal"""
    if request.method == 'POST':
        # Handle form submission
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            # AJAX request - return JSON response
            # Add your user creation logic here
            return JsonResponse({
                'success': True,
                'message': 'User created successfully!'
            })
        
        # Regular form submission
        messages.success(request, 'User created successfully!')
        return redirect('user_list')
    
    # GET request - render the form
    return render(request, 'posApp/user_form.html', {
        'form_title': 'Add New User'
    })

@login_required
def user_edit(request):
    """Handle user editing via modal"""
    user_id = request.GET.get('id')
    user_obj = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        # Handle form submission
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            # AJAX request - return JSON response
            # Add your user update logic here
            return JsonResponse({
                'success': True,
                'message': 'User updated successfully!'
            })
        
        # Regular form submission
        messages.success(request, 'User updated successfully!')
        return redirect('user_list')
    
    # GET request - render the form
    return render(request, 'posApp/user_form.html', {
        'form_title': f'Edit User: {user_obj.username}',
        'user_obj': user_obj
    })

@require_POST
@login_required
def user_delete(request):
    """Handle user deletion via AJAX"""
    user_id = request.POST.get('id')
    user_obj = get_object_or_404(User, id=user_id)
    
    # Prevent deletion of superusers
    if user_obj.is_superuser:
        return JsonResponse({
            'success': False, 
            'message': 'Cannot delete superuser accounts!'
        })
    
    username = user_obj.username
    user_obj.delete()
    
    return JsonResponse({
        'success': True,
        'message': f'User {username} has been deleted successfully!'
    })

# User Management Views
@login_required
@user_passes_test(is_admin_or_manager)
@login_required
def user_list(request):
    """List all users with pagination and search functionality"""
    search_query = request.GET.get('search', '')
    
    users = User.objects.all().order_by('-date_joined')
    
    if search_query:
        users = users.filter(
            username__icontains=search_query
        ) | users.filter(
            email__icontains=search_query
        ) | users.filter(
            first_name__icontains=search_query
        ) | users.filter(
            last_name__icontains=search_query
        )
    
    paginator = Paginator(users, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'active_users': User.objects.filter(is_active=True).count(),
        'staff_users': User.objects.filter(is_staff=True).count(),
    }
    return render(request, 'posApp/user_list_test.html', context)

@login_required
def user_create(request):
    """Handle user creation via modal"""
    if request.method == 'POST':
        form = UserForm(request.POST)
        if form.is_valid():
            form.save()
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': True, 'message': 'User created successfully!'})
            messages.success(request, 'User created successfully!')
            return redirect('user_list')
    else:
        form = UserForm()
    
    return render(request, 'posApp/user_form.html', {
        'form_title': 'Add New User',
        'form': form
    })

@login_required
def user_edit(request):
    """Handle user editing via modal"""
    user_id = request.GET.get('id')
    user_obj = get_object_or_404(User, id=user_id)

    if request.method == 'POST':
        form = UserForm(request.POST, instance=user_obj)
        if form.is_valid():
            form.save()
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': True, 'message': 'User updated successfully!'})
            messages.success(request, 'User updated successfully!')
            return redirect('user_list')
    else:
        form = UserForm(instance=user_obj)

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return render(request, 'posApp/partials/edit_user_form.html', {
            'form_title': f'Edit User: {user_obj.username}',
            'form': form,
            'user_obj': user_obj
        })

    return HttpResponseBadRequest("Invalid request")

@login_required
def user_delete(request):
    """Handle user deletion via AJAX or GET"""
    if request.method == 'POST':
        user_id = request.POST.get('id')
        user_obj = get_object_or_404(User, id=user_id)

        if user_obj.is_superuser:
            return JsonResponse({'success': False, 'message': 'Cannot delete superuser accounts!'})
        
        username = user_obj.username
        user_obj.delete()
        return JsonResponse({'success': True, 'message': f'User {username} has been deleted successfully!'})

    user_id = request.GET.get('id')
    user_obj = get_object_or_404(User, id=user_id)

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return render(request, 'posApp/partials/delete_user_confirm.html', {
            'user_obj': user_obj
        })

    return HttpResponseBadRequest("Invalid request")


@login_required
def user_toggle_status(request, user_id):
    """Toggle user active status via AJAX"""
    if request.method == 'POST':
        user_obj = get_object_or_404(User, id=user_id)
        
        # Don't allow deactivating superusers
        if user_obj.is_superuser and user_obj.is_active:
            return JsonResponse({
                'success': False, 
                'message': 'Cannot deactivate superuser accounts!'
            })
        
        user_obj.is_active = not user_obj.is_active
        user_obj.save()
        
        return JsonResponse({
            'success': True,
            'is_active': user_obj.is_active,
            'message': f'User {user_obj.username} {"activated" if user_obj.is_active else "deactivated"} successfully!'
        })
    
    return JsonResponse({'success': False, 'message': 'Invalid request method'})

# Employee Management Views
@login_required
@user_passes_test(is_admin_or_manager)
def employee_list(request):
    """List all employees"""
    employees = Employee.objects.all().order_by('-date_added')
    paginator = Paginator(employees, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'user_role': get_user_role(request.user),
    }
    return render(request, 'employees/employee_list.html', context)

@login_required
@user_passes_test(is_admin_or_manager)
def employee_create(request):
    """Create new employee"""
    if request.method == 'POST':
        form = EmployeeForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Employee created successfully!')
            return redirect('employee_list')
    else:
        form = EmployeeForm()
    
    context = {
        'form': form,
        'user_role': get_user_role(request.user),
    }
    return render(request, 'employees/employee_form.html', context)

@login_required
@user_passes_test(is_admin_or_manager)
def employee_edit(request, emp_id):
    """Edit employee"""
    employee = get_object_or_404(Employee, id=emp_id)
    
    if request.method == 'POST':
        form = EmployeeForm(request.POST, instance=employee)
        if form.is_valid():
            form.save()
            messages.success(request, 'Employee updated successfully!')
            return redirect('employee_list')
    else:
        form = EmployeeForm(instance=employee)
    
    context = {
        'form': form,
        'employee': employee,
        'user_role': get_user_role(request.user),
    }
    return render(request, 'employees/employee_form.html', context)

@login_required
@user_passes_test(is_admin_or_manager)
def employee_delete(request, emp_id):
    """Delete employee"""
    employee = get_object_or_404(Employee, id=emp_id)
    
    if request.method == 'POST':
        employee_name = str(employee)
        employee.delete()
        messages.success(request, f'Employee {employee_name} deleted successfully!')
        return redirect('employee_list')
    
    context = {
        'employee': employee,
        'user_role': get_user_role(request.user),
    }
    return render(request, 'employees/employee_delete.html', context)

# POS System Views
@login_required
def pos(request):
    """Point of Sale interface - accessible to all roles"""
    products = Products.objects.filter(status = 1)
    product_json = []
    for product in products:
        product_json.append({'id':product.id, 'name':product.name, 'price':float(product.price)})
    context = {
        'page_title' : "Point of Sale",
        'products' : products,
        'product_json' : json.dumps(product_json),
        'user_role': get_user_role(request.user),
    }
    return render(request, 'posApp/pos.html', context)

@login_required
def checkout_modal(request):
    grand_total = 0
    if 'grand_total' in request.GET:
        grand_total = request.GET['grand_total']
    context = {
        'grand_total' : grand_total,
        'user_role': get_user_role(request.user),
    }
    return render(request, 'posApp/checkout.html', context)

@login_required
def save_pos(request):
    resp = {'status':'failed','msg':''}
    data = request.POST
    pref = datetime.now().year + datetime.now().year
    i = 1
    while True:
        code = '{:0>5}'.format(i)
        i += int(1)
        check = Sales.objects.filter(code = str(pref) + str(code)).all()
        if len(check) <= 0:
            break
    code = str(pref) + str(code)

    try:
        sales = Sales(code=code, sub_total = data['sub_total'], tax = data['tax'], tax_amount = data['tax_amount'], grand_total = data['grand_total'], tendered_amount = data['tendered_amount'], amount_change = data['amount_change']).save()
        sale_id = Sales.objects.last().pk
        i = 0
        for prod in data.getlist('product_id[]'):
            product_id = prod 
            sale = Sales.objects.filter(id=sale_id).first()
            product = Products.objects.filter(id=product_id).first()
            qty = data.getlist('qty[]')[i] 
            price = data.getlist('price[]')[i] 
            total = float(qty) * float(price)
            print({'sale_id' : sale, 'product_id' : product, 'qty' : qty, 'price' : price, 'total' : total})
            salesItems(sale_id = sale, product_id = product, qty = qty, price = price, total = total).save()
            i += int(1)
        resp['status'] = 'success'
        resp['sale_id'] = sale_id
        messages.success(request, "Sale Record has been saved.")
    except:
        resp['msg'] = "An error occured"
        print("Unexpected error:", sys.exc_info()[0])
    return HttpResponse(json.dumps(resp),content_type="application/json")

# Sales Management Views
@login_required
def salesList(request):
    """Sales list view - accessible to managers and admins"""
    if not is_admin_or_manager(request.user):
        return redirect('pos')
    
    sales = Sales.objects.all()
    sale_data = []
    for sale in sales:
        data = {}
        for field in sale._meta.get_fields(include_parents=False):
            if field.related_model is None:
                data[field.name] = getattr(sale,field.name)
        data['items'] = salesItems.objects.filter(sale_id = sale).all()
        data['item_count'] = len(data['items'])
        if 'tax_amount' in data:
            data['tax_amount'] = format(float(data['tax_amount']),'.2f')
        sale_data.append(data)
    
    context = {
        'page_title':'Sales Transactions',
        'sale_data':sale_data,
        'user_role': get_user_role(request.user),
    }
    return render(request, 'posApp/sales.html', context)

@login_required
def receipt(request):
    id = request.GET.get('id')
    sales = Sales.objects.filter(id = id).first()
    transaction = {}
    for field in Sales._meta.get_fields():
        if field.related_model is None:
            transaction[field.name] = getattr(sales,field.name)
    if 'tax_amount' in transaction:
        transaction['tax_amount'] = format(float(transaction['tax_amount']))
    ItemList = salesItems.objects.filter(sale_id = sales).all()
    context = {
        "transaction" : transaction,
        "salesItems" : ItemList,
        'user_role': get_user_role(request.user),
    }
    return render(request, 'posApp/receipt.html', context)

@login_required
def delete_sale(request):
    if not is_admin_or_manager(request.user):
        return JsonResponse({'status':'failed', 'msg':'Permission denied'})
    
    resp = {'status':'failed', 'msg':''}
    id = request.POST.get('id')
    try:
        delete = Sales.objects.filter(id = id).delete()
        resp['status'] = 'success'
        messages.success(request, 'Sale Record has been deleted.')
    except:
        resp['msg'] = "An error occured"
        print("Unexpected error:", sys.exc_info()[0])
    return HttpResponse(json.dumps(resp), content_type='application/json')

# Product and Category Management
@login_required
@user_passes_test(is_admin_or_manager)
def products(request):
    product_list = Products.objects.all()
    context = {
        'page_title':'Product List',
        'products':product_list,
        'user_role': get_user_role(request.user),
    }
    return render(request, 'posApp/products.html', context)

@login_required
@user_passes_test(is_admin_or_manager)
def manage_products(request):
    product = {}
    categories = Category.objects.filter(status = 1).all()
    if request.method == 'GET':
        data =  request.GET
        id = ''
        if 'id' in data:
            id= data['id']
        if id.isnumeric() and int(id) > 0:
            product = Products.objects.filter(id=id).first()
    
    context = {
        'product' : product,
        'categories' : categories,
        'user_role': get_user_role(request.user),
    }
    return render(request, 'posApp/manage_product.html', context)

@login_required
@user_passes_test(is_admin_or_manager)
def save_product(request):
    data = request.POST
    resp = {'status': 'failed'}
    id = ''
    if 'id' in data:
        id = data['id']
    
    category = Category.objects.filter(id=data['category_id']).first()
    
    try:
        if (data['id']).isnumeric() and int(data['id']) > 0:
            save_product = Products.objects.filter(id=data['id']).update(
                category_id=category, 
                name=data['name'], 
                description=data['description'], 
                price=float(data['price']),
                status=data['status']
            )
        else:
            save_product = Products(
                category_id=category, 
                name=data['name'], 
                description=data['description'], 
                price=float(data['price']),
                status=data['status']
            )
            save_product.save()
            resp['product_code'] = save_product.code
        
        resp['status'] = 'success'
        messages.success(request, 'Product Successfully saved.')
        
    except Exception as e:
        resp['status'] = 'failed'
        resp['msg'] = str(e)
    
    return HttpResponse(json.dumps(resp), content_type="application/json")

@login_required
@user_passes_test(is_admin_or_manager)
def delete_product(request):
    data =  request.POST
    resp = {'status':''}
    try:
        Products.objects.filter(id = data['id']).delete()
        resp['status'] = 'success'
        messages.success(request, 'Product Successfully deleted.')
    except:
        resp['status'] = 'failed'
    return HttpResponse(json.dumps(resp), content_type="application/json")

@login_required
@user_passes_test(is_admin_or_manager)
def category(request):
    category_list = Category.objects.all()
    context = {
        'page_title':'Category List',
        'category':category_list,
        'user_role': get_user_role(request.user),
    }
    return render(request, 'posApp/category.html', context)

@login_required
@user_passes_test(is_admin_or_manager)
def manage_category(request):
    category = {}
    if request.method == 'GET':
        data =  request.GET
        id = ''
        if 'id' in data:
            id= data['id']
        if id.isnumeric() and int(id) > 0:
            category = Category.objects.filter(id=id).first()
    
    context = {
        'category' : category,
        'user_role': get_user_role(request.user),
    }
    return render(request, 'posApp/manage_category.html', context)

@login_required
@user_passes_test(is_admin_or_manager)
def save_category(request):
    data =  request.POST
    resp = {'status':'failed'}
    try:
        if (data['id']).isnumeric() and int(data['id']) > 0 :
            save_category = Category.objects.filter(id = data['id']).update(name=data['name'], description = data['description'],status = data['status'])
        else:
            save_category = Category(name=data['name'], description = data['description'],status = data['status'])
            save_category.save()
        resp['status'] = 'success'
        messages.success(request, 'Category Successfully saved.')
    except:
        resp['status'] = 'failed'
    return HttpResponse(json.dumps(resp), content_type="application/json")

@login_required
@user_passes_test(is_admin_or_manager)
def delete_category(request):
    data =  request.POST
    resp = {'status':''}
    try:
        Category.objects.filter(id = data['id']).delete()
        resp['status'] = 'success'
        messages.success(request, 'Category Successfully deleted.')
    except:
        resp['status'] = 'failed'
    return HttpResponse(json.dumps(resp), content_type="application/json")

# Analytics Views
@login_required
@user_passes_test(is_admin_or_manager)
def get_chart_data(request):
    """API endpoint for dynamic chart data updates"""
    year = int(request.GET.get('year', datetime.now().year))
    month = int(request.GET.get('month', datetime.now().month))
    
    days_in_month = calendar.monthrange(year, month)[1]
    
    response_data = {
        'daily_sales': [],
        'top_products': [],
        'category_sales': [],
        'total_month_sales': 0
    }
    
    # Get all sales for the selected month
    month_sales = Sales.objects.filter(
        date_added__year=year,
        date_added__month=month
    )
    
    # Calculate total sales for the month
    total_sales = month_sales.aggregate(Sum('grand_total'))['grand_total__sum'] or 0
    response_data['total_month_sales'] = float(total_sales)
    
    # Get daily sales data
    daily_sales = month_sales.annotate(
        day=ExtractDay('date_added')
    ).values('day').annotate(
        total=Sum('grand_total')
    ).order_by('day')
    
    daily_sales_dict = {item['day']: float(item['total']) for item in daily_sales}
    for day in range(1, days_in_month + 1):
        response_data['daily_sales'].append({
            'day': str(day),
            'total': daily_sales_dict.get(day, 0)
        })
    
    # Get top 10 selling products for the month
    sales_items = salesItems.objects.filter(
        sale_id__date_added__year=year,
        sale_id__date_added__month=month
    ).values(
        'product_id',
        'product_id__name'
    ).annotate(
        qty_sum=Sum('qty'),
        total_sum=Sum('total')
    ).order_by('-qty_sum')[:10]
    
    for item in sales_items:
        response_data['top_products'].append({
            'name': item['product_id__name'],
            'qty': int(item['qty_sum']),
            'total': float(item['total_sum'])
        })
    
    # Get sales by category
    category_sales = salesItems.objects.filter(
        sale_id__date_added__year=year,
        sale_id__date_added__month=month
    ).values(
        'product_id__category_id',
        'product_id__category_id__name'
    ).annotate(
        count=Sum('qty')
    ).order_by('-count')
    
    for category in category_sales:
        if category['product_id__category_id__name']:
            response_data['category_sales'].append({
                'name': category['product_id__category_id__name'],
                'count': int(category['count'])
            })
    
    return JsonResponse(response_data)

# Miscellaneous Views
def about(request):
    context = {
        'page_title':'About',
        'user_role': get_user_role(request.user) if request.user.is_authenticated else None,
    }
    return render(request, 'posApp/about.html', context)
