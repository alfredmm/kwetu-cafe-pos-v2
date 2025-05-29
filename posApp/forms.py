# forms.py
from django import forms
from django.contrib.auth.models import User
from .models import Employee, Department, Position, UserRole

class EmployeeForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = [
            'user', 'firstname', 'middlename', 'lastname', 'gender', 'dob',
            'contact', 'address', 'email', 'department', 'position', 
            'date_hired', 'salary', 'status'
        ]
        widgets = {
            'firstname': forms.TextInput(attrs={'class': 'form-control'}),
            'middlename': forms.TextInput(attrs={'class': 'form-control'}),
            'lastname': forms.TextInput(attrs={'class': 'form-control'}),
            'gender': forms.Select(attrs={'class': 'form-control'}),
            'dob': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'contact': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'department': forms.Select(attrs={'class': 'form-control'}),
            'position': forms.Select(attrs={'class': 'form-control'}),
            'date_hired': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'salary': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'user': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only show users without employees
        self.fields['user'].queryset = User.objects.filter(employee__isnull=True)
        self.fields['user'].required = False

class UserRoleForm(forms.ModelForm):
    class Meta:
        model = UserRole
        fields = ['role', 'is_active']
        widgets = {
            'role': forms.Select(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class UserForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}), required=False)
    password_confirm = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}), required=False)
    role = forms.ChoiceField(choices=UserRole.ROLE_CHOICES, widget=forms.Select(attrs={'class': 'form-control'}))
    
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'is_active']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')
        
        if password and password != password_confirm:
            raise forms.ValidationError("Passwords don't match")
        
        return cleaned_data