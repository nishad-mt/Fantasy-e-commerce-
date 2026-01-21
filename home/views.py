from django.shortcuts import render
from products.models import Categories,Product
from django.views.decorators.cache import never_cache
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from products.models import Categories,Product
from django.shortcuts import get_object_or_404
from .models import SiteContact
from django.http import JsonResponse
from .forms import SiteContactForm
from accounts.decarators import admin_required
from .models import SiteContact,ContactMessage

def home(request):
    category = Categories.objects.all()[:5]
    products = Product.objects.filter(is_active = True).order_by('-created_at')[:5]
    context = {
        'category':category,
        'products':products,
        
    }
    return render(request,'index.html',context)

def about(request):
    return render(request,'aboutus.html')

def contact(request):
    contact_details = SiteContact.objects.get(id=1)
    return render(request,'contact.html',{"contact": contact_details})

@admin_required
def update_site_contact(request):
    contact, _ = SiteContact.objects.get_or_create(id=1)

    if request.method == "POST":
        form = SiteContactForm(request.POST, instance=contact)

        if form.is_valid():
            form.save()
            return JsonResponse({"success": True})

        return JsonResponse({"success": False, "errors": form.errors})

@login_required
@never_cache
def contact_message(request):
    if request.method == "POST":
        ContactMessage.objects.create(
            user=request.user if request.user.is_authenticated else None,
            name=request.POST.get("name"),
            number=request.POST.get("number"),
            category=request.POST.get("category"),
            message=request.POST.get("message"),
        )
        return JsonResponse({"success": True})

    return JsonResponse({"success": False})
