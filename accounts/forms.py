from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import User


class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={"placeholder": "Email"}))
    first_name = forms.CharField(max_length=30, required=True, widget=forms.TextInput(attrs={"placeholder": "First Name"}))
    last_name = forms.CharField(max_length=30, required=True, widget=forms.TextInput(attrs={"placeholder": "Last Name"}))

    class Meta:
        model = User
        fields = ("username", "email", "first_name", "last_name", "password1", "password2")


class UserProfileForm(forms.ModelForm):
    first_name = forms.CharField(max_length=30, required=True, widget=forms.TextInput(attrs={"placeholder": "First Name"}))
    last_name = forms.CharField(max_length=30, required=True, widget=forms.TextInput(attrs={"placeholder": "Last Name"}))
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={"placeholder": "Email"}))

    class Meta:
        model = User
        fields = ("first_name", "last_name", "email", "phone_number")
        widgets = {
            "phone_number": forms.TextInput(attrs={"placeholder": "+92XXXXXXXXXX"}),
        }
