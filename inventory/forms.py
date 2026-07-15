from django import forms

from .models import StockMovement


class StockAdjustmentForm(forms.ModelForm):
    class Meta:
        model = StockMovement
        fields = ("product", "movement_type", "quantity", "reference", "notes")
        widgets = {
            "product": forms.Select(attrs={}),
            "movement_type": forms.Select(attrs={}),
            "quantity": forms.NumberInput(attrs={"placeholder": "e.g. 10 for IN, -5 for OUT"}),
            "reference": forms.TextInput(attrs={"placeholder": "e.g. Invoice #INV-001, Order #123"}),
            "notes": forms.Textarea(attrs={"placeholder": "Optional notes", "rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from products.models import Product
        self.fields["product"].queryset = Product.objects.filter(is_active=True, is_deleted=False)
        self.fields["reference"].required = False
        self.fields["notes"].required = False

    def clean_quantity(self):
        quantity = self.cleaned_data.get("quantity")
        if quantity == 0:
            raise forms.ValidationError("Quantity cannot be zero.")
        return quantity
