from django import forms

from customers.models import Order, OrderItem
from products.models import Product


class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ["customer", "payment_method", "status", "notes"]
        widgets = {
            "customer": forms.Select(attrs={"class": "apple-form-select"}),
            "payment_method": forms.Select(attrs={"class": "apple-form-select"}),
            "status": forms.Select(attrs={"class": "apple-form-select"}),
            "notes": forms.Textarea(attrs={"class": "apple-form-input", "rows": 3, "placeholder": "Optional notes"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from customers.models import Customer
        self.fields["customer"].queryset = Customer.objects.filter(is_deleted=False)


class OrderItemForm(forms.ModelForm):
    class Meta:
        model = OrderItem
        fields = ["product", "quantity", "unit_price"]
        widgets = {
            "product": forms.Select(attrs={"class": "apple-form-select product-select"}),
            "quantity": forms.NumberInput(attrs={"class": "apple-form-input quantity-input", "min": "1", "value": "1"}),
            "unit_price": forms.NumberInput(attrs={"class": "apple-form-input unit-price-input", "step": "0.01", "min": "0"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["product"].queryset = Product.objects.filter(is_active=True, is_deleted=False)
        self.fields["unit_price"].required = False


OrderItemFormSet = forms.inlineformset_factory(
    Order,
    OrderItem,
    form=OrderItemForm,
    extra=1,
    can_delete=True,
    min_num=1,
    validate_min=True,
)


class PaymentForm(forms.ModelForm):
    class Meta:
        from .models import Payment
        model = Payment
        fields = ["amount", "payment_method", "transaction_id", "notes"]
        widgets = {
            "amount": forms.NumberInput(attrs={"class": "apple-form-input", "step": "0.01", "min": "0.01"}),
            "payment_method": forms.Select(attrs={"class": "apple-form-select"}),
            "transaction_id": forms.TextInput(attrs={"class": "apple-form-input", "placeholder": "External reference (optional)"}),
            "notes": forms.Textarea(attrs={"class": "apple-form-input", "rows": 2, "placeholder": "Optional notes"}),
        }


class QuickSaleForm(forms.Form):
    """Quick sale form for POS-style order creation."""
    customer = forms.ModelChoiceField(
        queryset=None,
        required=False,
        empty_label="Walk-in Customer",
        widget=forms.Select(attrs={"class": "apple-form-select"}),
    )
    payment_method = forms.ChoiceField(
        choices=Order.PaymentMethod.choices,
        initial=Order.PaymentMethod.CASH,
        widget=forms.Select(attrs={"class": "apple-form-select"}),
    )
    discount_code = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"class": "apple-form-input", "placeholder": "Discount or coupon code"}),
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"class": "apple-form-input", "rows": 2, "placeholder": "Optional notes"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from customers.models import Customer
        self.fields["customer"].queryset = Customer.objects.filter(is_deleted=False)
