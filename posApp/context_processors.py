from .models import UserRole # Import the model

def get_user_role(user):
    """Get user role"""
    if user.is_superuser:
        return 'admin'
    try:
        user_role = UserRole.objects.get(user=user)
        return user_role.role
    except UserRole.DoesNotExist:
        return 'waiter'  # default role

def user_role_context(request):
    """Add user role to all templates"""
    if request.user.is_authenticated:
        user_role = get_user_role(request.user)
        return {
            'user_role': user_role,
            'show_admin_menu': user_role in ['admin', 'manager'],
            'show_pos_only': user_role == 'waiter',
        }
    return {}
