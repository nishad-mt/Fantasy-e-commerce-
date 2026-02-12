from django.shortcuts import render, redirect, get_object_or_404
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

from payments.models import Payment
from order.models import Order
from cart.models import CartItem
from django.db import transaction
from django.views.decorators.cache import never_cache
from decimal import Decimal

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
        status="PENDING_PAYMENT",
        payment_status="PENDING"
    )

    # 🔑 STEP 1: check if payment already exists
    payment = Payment.objects.filter(order=order).first()

    if payment and payment.razorpay_order_id:
        # Razorpay order already created → REUSE it
        razorpay_order_id = payment.razorpay_order_id
    else:
        # 🔑 STEP 2: create Razorpay order ONLY ONCE
        client = razorpay.Client(
            auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
        )

        razorpay_order = client.order.create({
            "amount": int(order.total_amount * 100),
            "currency": "INR",
            "payment_capture": 1
        })

        # 🔑 STEP 3: create or update Payment safely
        if not payment:
            payment = Payment.objects.create(
                order=order,
                user=request.user,
                amount=order.total_amount,
                status="CREATED",
                razorpay_order_id=razorpay_order["id"],
            )
        else:
            payment.razorpay_order_id = razorpay_order["id"]
            payment.save(update_fields=["razorpay_order_id"])

        razorpay_order_id = razorpay_order["id"]

    return JsonResponse({
        "razorpay_order_id": razorpay_order_id,
        "key": settings.RAZORPAY_KEY_ID,
        "amount": int(payment.amount * 100),
        "currency": "INR",
    })

@csrf_exempt
@transaction.atomic
def razorpay_webhook(request):
    if request.method != "POST":
        return HttpResponse(status=400)

    payload = request.body
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

    data = json.loads(payload.decode())
    event = data.get("event")

    # Only process payment related events
    if not event or not event.startswith("payment."):
        return HttpResponse(status=200)

    entity = data["payload"]["payment"]["entity"]
    razorpay_order_id = entity.get("order_id")

    payment = Payment.objects.select_related("order").filter(
        razorpay_order_id=razorpay_order_id
    ).first()

    if not payment:
        return HttpResponse(status=200)

    order = payment.order

    # HANDLE PAYMENT FAILED

    if event == "payment.failed":

        # Do not overwrite successful payments
        if payment.status != "SUCCESS":
            payment.razorpay_payment_id = entity.get("id")
            payment.gateway_method = entity.get("method")
            payment.status = "FAILED"
            payment.save(update_fields=[
                "razorpay_payment_id",
                "gateway_method",
                "status"
            ])

            order.payment_status = "FAILED"
            order.save(update_fields=["payment_status"])

        return HttpResponse(status=200)

    # HANDLE PAYMENT SUCCESS

    if event == "payment.captured":

        # Idempotency protection
        if payment.status == "SUCCESS":
            return HttpResponse(status=200)

        # Amount verification (security check)
        if entity["amount"] != int(payment.amount * 100):
            return HttpResponse(status=400)

        payment.razorpay_payment_id = entity["id"]
        payment.gateway_method = entity.get("method")
        payment.status = "SUCCESS"
        payment.save(update_fields=[
            "razorpay_payment_id",
            "gateway_method",
            "status"
        ])

        order.payment_status = "SUCCESS"
        order.status = "CONFIRMED"
        order.paid_at = timezone.now()
        order.save(update_fields=[
            "payment_status",
            "status",
            "paid_at"
        ])

        CartItem.objects.filter(cart__user=order.user).delete()

        return HttpResponse(status=200)

    # Ignore other events safely
    return HttpResponse(status=200)

@never_cache
@login_required
@transaction.atomic
def success(request, order_id):

    # ✅ Try to mark success_viewed atomically
    updated = Order.objects.filter(
        order_id=order_id,
        user=request.user,
        payment_status="SUCCESS",
        success_viewed=False
    ).update(success_viewed=True)

    # ❌ If no row was updated → already viewed or invalid
    if updated == 0:
        return redirect("order_detail", order_id=order_id)

    # ✅ First and ONLY allowed render
    order = Order.objects.get(order_id=order_id)

    return render(request, "success.html", {
        "order": order
    })