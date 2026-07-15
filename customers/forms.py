from django import forms

from .models import Customer


class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = ("first_name", "last_name", "email", "phone", "address", "city", "notes")
        widgets = {
            "first_name": forms.TextInput(attrs={"placeholder": "First name"}),
            "last_name": forms.TextInput(attrs={"placeholder": "Last name"}),
            "email": forms.EmailInput(attrs={"placeholder": "email@example.com"}),
            "phone": forms.TextInput(attrs={"placeholder": "+92XXXXXXXXXX"}),
            "address": forms.Textarea(attrs={"placeholder": "Address", "rows": 3}),
            "city": forms.TextInput(attrs={"placeholder": "City"}),
            "notes": forms.Textarea(attrs={"placeholder": "Optional notes", "rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].required = False
        self.fields["phone"].required = False
