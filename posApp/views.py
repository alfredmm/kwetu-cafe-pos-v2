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
from .context_processors import get_user_role, user_role_context  # Add any other functions you need
from django.core.paginator import Paginator


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
                resp['redirect_url'] = '/'
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
    if not is_admin_or_manager(request.user):
        return redirect('pos')
    sales = Sales.objects.all().order_by('-date_added')
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
    paginator = Paginator(sale_data, 20)  # 20 per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {
        'page_title':'Sales Transactions',
        'sale_data':page_obj,
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

import requests
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import MpesaTransaction
import base64
from datetime import datetime, timedelta
import json
import logging
from django.core.paginator import Paginator
from django.db.models import Q
from django.conf import settings



logger = logging.getLogger(__name__)

# M-Pesa Express Sandbox Credentials
consumer_key = settings.MPESA_CONFIG['CONSUMER_KEY']
consumer_secret = settings.MPESA_CONFIG['CONSUMER_SECRET']
business_short_code = settings.MPESA_CONFIG['BUSINESS_SHORT_CODE']
passkey = settings.MPESA_CONFIG['PASS_KEY']
callback_url = settings.MPESA_CONFIG['CALLBACK_URL']

def get_access_token():
    """Get OAuth access token for M-Pesa Express"""
    api_url = 'https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials'
    
    # For M-Pesa Express sandbox, use the Pass Key as both consumer key and secret
    consumer_key = settings.MPESA_CONFIG['CONSUMER_KEY']
    consumer_secret = settings.MPESA_CONFIG['CONSUMER_SECRET']
    
    # Create basic auth header
    auth_string = f"{consumer_key}:{consumer_secret}"
    auth_bytes = auth_string.encode('utf-8')
    auth_header = base64.b64encode(auth_bytes).decode('utf-8')
    
    headers = {
        'Authorization': f'Basic {auth_header}',
        'Content-Type': 'application/json'
    }
    
    try:
        logger.info("Requesting access token...")
        response = requests.get(api_url, headers=headers)
        response.raise_for_status()
        response_data = response.json()
        
        access_token = response_data.get('access_token')
        if access_token:
            logger.info("Access token obtained successfully")
            return access_token
        else:
            logger.error(f"No access token in response: {response_data}")
            return None
            
    except Exception as e:
        logger.error(f"Failed to get access token: {str(e)}")
        if hasattr(e, 'response') and e.response:
            logger.error(f"Response: {e.response.text}")
        return None

def mpesa_home(request):
    if request.method == 'POST':
        phone = request.POST.get('phone')
        amount = request.POST.get('amount')
        
        if phone and amount:
            # Format phone number to 254XXXXXXXX
            if phone.startswith('0'):
                phone = '254' + phone[1:]
            elif phone.startswith('+254'):
                phone = phone[1:]
            elif not phone.startswith('254'):
                # Add 254 prefix if not present
                phone = '254' + phone.lstrip('+')
                
            result = initiate_stk_push(request, phone, amount)
            
            # If it's an AJAX request, return JSON
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return result
            
            return result
    
    return render(request, 'payments/home.html')

def initiate_stk_push(request, phone, amount):
    # Get access token first
    access_token = get_access_token()
    if not access_token:
        error_msg = "Failed to authenticate with M-Pesa API"
        logger.error(error_msg)
        
        # Return JSON for AJAX requests
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'error': error_msg}, status=500)
        return render(request, 'payments/error.html', {'error': error_msg})
    
    # STK Push API endpoint
    api_url = 'https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest'
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    business_short_code = settings.MPESA_CONFIG['BUSINESS_SHORT_CODE']
    passkey = settings.MPESA_CONFIG['PASS_KEY']
    
    # Generate password for STK Push
    password_str = f"{business_short_code}{passkey}{timestamp}"
    password = base64.b64encode(password_str.encode()).decode()
    
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    payload = {
        "BusinessShortCode": business_short_code,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": int(amount),
        "PartyA": phone,
        "PartyB": business_short_code,
        "PhoneNumber": phone,
        "CallBackURL": callback_url,
        "AccountReference": f"ORDER{timestamp}",
        "TransactionDesc": "Payment for goods and services"
    }
    
    try:
        logger.info(f"Initiating STK Push for {phone}, Amount: {amount}")
        logger.info(f"Payload: {json.dumps(payload, indent=2)}")
        
        response = requests.post(api_url, json=payload, headers=headers)
        logger.info(f"Response Status: {response.status_code}")
        logger.info(f"Response Text: {response.text}")
        
        response.raise_for_status()
        response_data = response.json()
        
        # Check if the STK push was initiated successfully
        if response_data.get('ResponseCode') == '0':
            merchant_request_id = response_data.get('MerchantRequestID')
            checkout_request_id = response_data.get('CheckoutRequestID')
            customer_message = response_data.get('CustomerMessage')
            
            if merchant_request_id and checkout_request_id:
                # Save transaction to database
                transaction = MpesaTransaction.objects.create(
                    merchant_request_id=merchant_request_id,
                    checkout_request_id=checkout_request_id,
                    phone_number=phone,
                    amount=amount,
                    raw_response=json.dumps(response_data),
                    status='Pending'
                )
                
                logger.info(f"STK Push initiated successfully. CheckoutRequestID: {checkout_request_id}")
                
                # Return JSON for AJAX requests
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': True,
                        'checkout_request_id': checkout_request_id,
                        'merchant_request_id': merchant_request_id,
                        'customer_message': customer_message,
                        'phone': phone,
                        'amount': amount
                    })
                
                return render(request, 'payments/payment_initiated.html', {
                    'phone': phone,
                    'amount': amount,
                    'transaction': transaction,
                    'customer_message': customer_message
                })
            else:
                error_msg = "Invalid response: Missing transaction IDs"
                logger.error(error_msg)
                
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'error': error_msg}, status=500)
                return render(request, 'payments/error.html', {'error': error_msg})
        else:
            error_msg = response_data.get('errorMessage', f"Request failed: {response_data}")
            logger.error(f"STK Push failed: {error_msg}")
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'error': error_msg}, status=500)
            return render(request, 'payments/error.html', {'error': error_msg})
        
    except requests.exceptions.RequestException as e:
        error_msg = f"Network error: {str(e)}"
        if hasattr(e, 'response') and e.response:
            try:
                error_response = e.response.json()
                error_msg = error_response.get('errorMessage', error_msg)
                logger.error(f"API Error Response: {error_response}")
            except:
                error_msg += f" | Response: {e.response.text}"
        logger.error(error_msg)
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'error': error_msg}, status=500)
        return render(request, 'payments/error.html', {'error': error_msg})
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'error': str(e)}, status=500)
        return render(request, 'payments/error.html', {'error': str(e)})

@csrf_exempt
def callback_handler(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            logger.info(f"Received M-Pesa callback: {json.dumps(data, indent=2)}")
            
            stk_callback = data.get('Body', {}).get('stkCallback', {})
            result_code = stk_callback.get('ResultCode')
            result_desc = stk_callback.get('ResultDesc')
            checkout_request_id = stk_callback.get('CheckoutRequestID')
            
            if checkout_request_id:
                try:
                    transaction = MpesaTransaction.objects.get(checkout_request_id=checkout_request_id)
                    
                    if result_code == 0:  # Payment successful
                        callback_metadata = stk_callback.get('CallbackMetadata', {})
                        items = callback_metadata.get('Item', [])
                        
                        for item in items:
                            name = item.get('Name')
                            value = item.get('Value')
                            
                            if name == 'MpesaReceiptNumber':
                                transaction.receipt_number = value
                            elif name == 'Amount':
                                transaction.amount = value
                            elif name == 'TransactionDate':
                                try:
                                    transaction.transaction_date = datetime.strptime(str(value), '%Y%m%d%H%M%S')
                                except ValueError:
                                    logger.warning(f"Could not parse transaction date: {value}")
                        
                        transaction.status = 'Completed'
                        logger.info(f"Payment completed for {checkout_request_id}. Receipt: {transaction.receipt_number}")
                        
                    else:
                        # Payment failed, cancelled, or timed out
                        transaction.status = 'Failed'
                        
                        # Store the failure reason in raw_response
                        current_raw = {}
                        try:
                            if transaction.raw_response:
                                current_raw = json.loads(transaction.raw_response)
                        except (json.JSONDecodeError, TypeError):
                            pass
                        
                        # Add callback result to raw response
                        current_raw.update({
                            'callback_result_code': result_code,
                            'callback_result_desc': result_desc,
                            'ResultDesc': result_desc  # For easier access
                        })
                        
                        transaction.raw_response = json.dumps(current_raw)
                        
                        logger.info(f"Payment failed for {checkout_request_id}. Code: {result_code}, Reason: {result_desc}")
                    
                    transaction.save()
                    
                except MpesaTransaction.DoesNotExist:
                    logger.warning(f"Transaction not found for CheckoutRequestID: {checkout_request_id}")
            
            return JsonResponse({'ResultCode': 0, 'ResultDesc': 'Callback processed successfully'})
            
        except json.JSONDecodeError:
            logger.error("Invalid JSON in callback request")
            return JsonResponse({'ResultCode': 1, 'ResultDesc': 'Invalid JSON format'})
        except Exception as e:
            logger.error(f"Callback processing error: {str(e)}")
            return JsonResponse({'ResultCode': 1, 'ResultDesc': 'Processing failed'})
    
    return JsonResponse({'ResultCode': 1, 'ResultDesc': 'Only POST method allowed'})

def check_transaction_status(request, checkout_request_id):
    """Check transaction status for real-time updates"""
    logger.info(f"Status check requested for: {checkout_request_id}")
    
    try:
        transaction = MpesaTransaction.objects.get(checkout_request_id=checkout_request_id)
        logger.info(f"Found transaction: {transaction.status}")
        
        response_data = {
            'status': transaction.status,
            'phone_number': transaction.phone_number,
            'amount': str(transaction.amount),
            'checkout_request_id': transaction.checkout_request_id
        }
        
        if transaction.status == 'Completed':
            response_data.update({
                'receipt_number': transaction.receipt_number,
                'transaction_date': transaction.transaction_date.isoformat() if transaction.transaction_date else None
            })
        elif transaction.status == 'Failed':
            # Try to extract failure reason from raw response or callback data
            failure_reason = 'Payment failed'
            try:
                if transaction.raw_response:
                    raw_data = json.loads(transaction.raw_response)
                    failure_reason = raw_data.get('ResultDesc', failure_reason)
            except (json.JSONDecodeError, TypeError):
                logger.warning(f"Could not parse raw response for transaction {checkout_request_id}")
                
            response_data['reason'] = failure_reason
            logger.info(f"Transaction failed with reason: {failure_reason}")
                
        return JsonResponse(response_data)
        
    except MpesaTransaction.DoesNotExist:
        logger.warning(f"Transaction not found: {checkout_request_id}")
        return JsonResponse({'error': 'Transaction not found', 'status': 'NotFound'}, status=404)
    
def transaction_list(request):
    q = request.GET.get("q", "").strip()
    start_date = request.GET.get("start_date", "")
    end_date = request.GET.get("end_date", "")
    per_page = int(request.GET.get("per_page", 20))

    transactions = MpesaTransaction.objects.all()

    # ✅ Search phone number OR status (anywhere in text)
    if q:
        transactions = transactions.filter(
            Q(phone_number__icontains=q) | Q(status__icontains=q)
        )

    # ✅ Date range filter
    # if start_date and end_date:
    #     transactions = transactions.filter(date__range=[start_date, end_date])
    # # ...existing code...
    # ✅ Date range filter
    if start_date and end_date:
        transactions = transactions.filter(transaction_date__range=[start_date, end_date])
# ...existing code...
    # --- Pagination ---
    
    # Get transactions per page from URL, default to 20
    per_page = int(request.GET.get('per_page', 20))
    if per_page not in [20, 50, 100]:
        per_page = 20 # Sanitize input
        
    paginator = Paginator(transactions, per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'transactions': page_obj,
        'per_page': per_page,
    }
    return render(request, 'payments/transactions.html', context)
