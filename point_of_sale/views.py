from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from .models import StoreSettings
from .forms import StoreSettingsForm


@login_required
def settings_view(request):
    settings_obj = StoreSettings.load()

    if request.method == "POST":
        form = StoreSettingsForm(request.POST, request.FILES, instance=settings_obj)
        if form.is_valid():
            form.save()
            messages.success(request, "Store settings updated successfully!")
            return redirect("settings")
    else:
        form = StoreSettingsForm(instance=settings_obj)

    return render(request, "core/settings.html", {"form": form, "settings_obj": settings_obj})
