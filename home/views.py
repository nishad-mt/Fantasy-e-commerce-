from django.shortcuts import render
from products.models import Categories,Product
from django.views.decorators.cache import never_cache
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from products.models import Categories,Product
from .models import SiteContact
from django.http import JsonResponse
from .forms import SiteContactForm
from accounts.decarators import admin_required
from .models import SiteContact,ContactMessage
from django.http import JsonResponse
from django.utils import timezone
import json
from django.core.mail import send_mail
from django.conf import settings


def home(request):
    category = Categories.objects.all()[:5]
    products = Product.objects.filter(is_active = True).order_by('-created_at')[:5]
    
    context = {
        'category':category,
        'products':products,
        
    }
    return render(request,'index.html',context)

def about(request):
    contact_details = SiteContact.objects.get(id=1)
    return render(request,'aboutus.html',{"contact_details":contact_details})

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
            email = request.POST.get("email"),
            name=request.POST.get("name"),
            number=request.POST.get("number"),
            category=request.POST.get("category"),
            message=request.POST.get("message"),
        )
        return JsonResponse({"success": True})

    return JsonResponse({"success": False})


@admin_required
def reply_contact_message(request):
    if request.method == "POST":
        data = json.loads(request.body)

        msg = ContactMessage.objects.get(id=data["message_id"])

        if msg.status == "replied":
            return JsonResponse({
                "success": False,
                "error": "Already replied"
            })

        msg.reply = data["reply"]
        msg.status = "replied"
        msg.replied_at = timezone.now()
        msg.save()

        if msg.email:
            send_mail(
                subject="Reply from Fantasy Bakery Support",
                message=f"""
Hello {msg.name},

Thank you for contacting Fantasy Bakery.

Here is our reply to your message:
----------------------------------
{msg.reply}
----------------------------------

If you need further assistance, feel free to contact us again.

Regards,
Fantasy Bakery Support Team
""",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[msg.email],
                fail_silently=False,
            )

        return JsonResponse({"success": True})

    return JsonResponse({"success": False})
