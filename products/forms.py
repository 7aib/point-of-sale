from django import forms

from .models import Category, Product


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ("name", "slug", "description", "parent", "is_active", "sort_order")
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "Category name"}),
            "slug": forms.TextInput(attrs={"placeholder": "auto-generated"}),
            "description": forms.Textarea(attrs={"placeholder": "Optional description", "rows": 3}),
            "parent": forms.Select(attrs={}),
            "sort_order": forms.NumberInput(attrs={"placeholder": "0"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["parent"].queryset = Category.objects.all()
        self.fields["parent"].empty_label = "-- No parent (root category) --"
        self.fields["slug"].required = False


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = (
            "name", "slug", "description", "sku", "barcode", "category",
            "cost_price", "selling_price", "stock_quantity", "low_stock_threshold",
            "tax_rate", "image", "is_active",
        )
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "Product name"}),
            "slug": forms.TextInput(attrs={"placeholder": "auto-generated"}),
            "description": forms.Textarea(attrs={"placeholder": "Product description", "rows": 3}),
            "sku": forms.TextInput(attrs={"placeholder": "e.g. PROD-001"}),
            "barcode": forms.TextInput(attrs={"placeholder": "e.g. 5901234123457", "class": "form-control", "autocomplete": "off"}),
            "category": forms.Select(),
            "cost_price": forms.NumberInput(attrs={"placeholder": "0.00", "step": "0.01"}),
            "selling_price": forms.NumberInput(attrs={"placeholder": "0.00", "step": "0.01"}),
            "stock_quantity": forms.NumberInput(attrs={"placeholder": "0"}),
            "low_stock_threshold": forms.NumberInput(attrs={"placeholder": "10"}),
            "tax_rate": forms.NumberInput(attrs={"placeholder": "0.00", "step": "0.01"}),
            "image": forms.FileInput(attrs={}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = Category.objects.filter(is_active=True)
        self.fields["slug"].required = False
        self.fields["barcode"].required = False
        self.fields["image"].required = False
