from django.shortcuts import render,redirect, get_object_or_404
from .forms import AddressForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from addresses.models import Address

User = get_user_model()

@login_required
def create_address(request):
    if request.method == "POST":
        form = AddressForm(request.POST)
        
        if form.is_valid():
            #The form doesn’t include user, so you must attach it before saving.
            address = form.save(commit=False)
            address.user = request.user
            address.save()
            return redirect("profile")
    else:    
        form = AddressForm()
    return render(request,"address_form.html",{'form':form})

@login_required
def set_default_address(request, address_id):
    address = get_object_or_404(Address, id=address_id, user=request.user)

    # Remove default from all addresses of this user
    Address.objects.filter(user=request.user, is_default=True).update(is_default=False)

    # Set selected one as default
    address.is_default = True
    address.save()

    return redirect("profile")

@login_required
def edit_address(request, address_id):
    address = get_object_or_404(Address, id=address_id, user=request.user)

    if request.method == "POST":
        form = AddressForm(request.POST, instance=address)
        if form.is_valid():
            form.save()
            return redirect("profile")
    else:
        form = AddressForm(instance=address)

    return render(request, "address_form.html", {
        "form": form,
        "edit": True
    })
    
@login_required
def delete_address(request, address_id):
    address = get_object_or_404(Address, id=address_id, user=request.user)

    # Prevent deleting default if it's the only one
    if address.is_default and Address.objects.filter(user=request.user).count() > 1:
        new_default = Address.objects.filter(user=request.user).exclude(id=address.id).first()
        new_default.is_default = True
        new_default.save()

    address.delete()
    return redirect("profile")
