from django.shortcuts import render, get_object_or_404
from django.conf import settings
from django.http import JsonResponse, HttpResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt, csrf_protect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from promotions.models import PromotionUsage

import razorpay
import hmac
import json
import hashlib
import razorpay

from payment.models import Payment
from order.models import Order
from cart.models import Cart

@csrf_protect
@login_required
def create_razorpay_order(request):
    if request.method != "POST":
        return HttpResponseBadRequest("Invalid request")

    order_id = request.POST.get("order_id")
    if not order_id:
        return HttpResponseBadRequest("Order ID missing")

    order = get_object_or_404(
        Order,
        order_id=order_id,
        user=request.user,
        status="PENDING",
        payment_status="PENDING"
    )

    payment, created = Payment.objects.get_or_create(
        order=order,
        defaults={
            "user": request.user,
            "amount": order.total_amount,
            "status": "CREATED"
        }
    )

    if created:
        client = razorpay.Client(
            auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
        )

        razorpay_order = client.order.create({
            "amount": int(order.total_amount * 100),
            "currency": "INR",
            "payment_capture": 1
        })

        payment.razorpay_order_id = razorpay_order["id"]
        payment.save()

    return JsonResponse({
        "razorpay_order_id": payment.razorpay_order_id,
        "key": settings.RAZORPAY_KEY_ID,
        "amount": int(payment.amount * 100),
        "currency": "INR",
    })


@csrf_exempt
def razorpay_webhook(request):
    payload = request.body.decode()
    signature = request.META.get("HTTP_X_RAZORPAY_SIGNATURE")

    if not signature:
        return HttpResponse(status=400)

    client = razorpay.Client(
        auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
    )

    try:
        client.utility.verify_webhook_signature(
            payload,
            signature,
            settings.RAZORPAY_WEBHOOK_SECRET
        )
    except razorpay.errors.SignatureVerificationError:
        return HttpResponse(status=400)

    data = json.loads(payload)

    if data.get("event") != "payment.captured":
        return HttpResponse(status=200)

    entity = data["payload"]["payment"]["entity"]
    razorpay_order_id = entity["order_id"]
    paid_amount = entity["amount"] / 100

    payment = Payment.objects.select_related("order").filter(
        razorpay_order_id=razorpay_order_id
    ).first()

    if not payment or payment.status == "SUCCESS":
        return HttpResponse(status=200)

    if paid_amount != payment.amount:
        return HttpResponse(status=400)

    order = payment.order

    payment.razorpay_payment_id = entity["id"]
    payment.gateway_method = entity["method"]
    payment.status = "SUCCESS"
    payment.save()

    order.payment_status = "SUCCESS"
    order.status = "CONFIRMED"
    order.paid_at = timezone.now()
    order.save()

    # 🔒 Lock coupon ONLY here
    if order.discount_type == "COUPON" and order.coupon:
        PromotionUsage.objects.get_or_create(
            user=order.user,
            promotion=order.coupon,
            order=order
        )

    # 🧹 Clear cart
    Cart.objects.filter(user=order.user).update(items=None)

    return HttpResponse(status=200)

def success(request):
    return render(request, "success.html")
