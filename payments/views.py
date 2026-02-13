from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
from django.http import JsonResponse, HttpResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt, csrf_protect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db import transaction
from django.views.decorators.cache import never_cache

from decimal import Decimal
import razorpay
import json
import logging

from promotions.models import PromotionUsage
from payments.models import Payment
from order.models import Order
from cart.models import CartItem


# LOGGER (NEW - production debugging)

logger = logging.getLogger(__name__)


# CREATE RAZORPAY ORDER

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

    payment = Payment.objects.filter(order=order).first()

    if payment and payment.razorpay_order_id:
        razorpay_order_id = payment.razorpay_order_id
        logger.info(f"Reusing Razorpay order {razorpay_order_id}")

    else:
        client = razorpay.Client(
            auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
        )

        razorpay_order = client.order.create({
            "amount": int(order.total_amount * 100),
            "currency": "INR",
            "payment_capture": 1
        })

        razorpay_order_id = razorpay_order["id"]

        if not payment:
            payment = Payment.objects.create(
                order=order,
                user=request.user,
                amount=order.total_amount,
                status="CREATED",
                razorpay_order_id=razorpay_order_id,
            )
        else:
            payment.razorpay_order_id = razorpay_order_id
            payment.save(update_fields=["razorpay_order_id"])

        logger.info(f"Created Razorpay order {razorpay_order_id}")

    return JsonResponse({
        "razorpay_order_id": razorpay_order_id,
        "key": settings.RAZORPAY_KEY_ID,
        "amount": int(payment.amount * 100),
        "currency": "INR",
    })


# RAZORPAY WEBHOOK

@csrf_exempt
@transaction.atomic
def razorpay_webhook(request):

    if request.method != "POST":
        return HttpResponse(status=400)

    payload = request.body
    signature = request.META.get("HTTP_X_RAZORPAY_SIGNATURE")

    if not signature:
        logger.warning("Webhook missing signature")
        return HttpResponse(status=400)

    client = razorpay.Client(
        auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
    )

    # VERIFY WEBHOOK SIGNATURE

    try:
        client.utility.verify_webhook_signature(
            payload,
            signature,
            settings.RAZORPAY_WEBHOOK_SECRET
        )
    except razorpay.errors.SignatureVerificationError:
        logger.warning("Invalid webhook signature")
        return HttpResponse(status=400)

    data = json.loads(payload.decode())
    event = data.get("event")

    logger.info(f"Webhook event received: {event}")

    if not event or not event.startswith("payment."):
        return HttpResponse(status=200)

    entity = data["payload"]["payment"]["entity"]
    razorpay_order_id = entity.get("order_id")
    razorpay_payment_id = entity.get("id")

    payment = Payment.objects.select_related("order").filter(
        razorpay_order_id=razorpay_order_id
    ).first()

    if not payment:
        logger.warning(f"No payment found for order: {razorpay_order_id}")
        return HttpResponse(status=200)

    order = payment.order

    # HANDLE PAYMENT FAILED

    if event == "payment.failed":

        if payment.status != "SUCCESS":
            payment.razorpay_payment_id = razorpay_payment_id
            payment.gateway_method = entity.get("method")
            payment.status = "FAILED"
            payment.save(update_fields=[
                "razorpay_payment_id",
                "gateway_method",
                "status"
            ])

            order.payment_status = "FAILED"
            order.save(update_fields=["payment_status"])

            logger.info(f"Payment failed: {razorpay_payment_id}")

        return HttpResponse(status=200)

    # HANDLE PAYMENT SUCCESS

    if event == "payment.captured":

        # Idempotency protection
        if payment.status == "SUCCESS":
            logger.info("Duplicate webhook ignored")
            return HttpResponse(status=200)

        # Amount verification (critical)
        if entity["amount"] != int(payment.amount * 100):
            logger.error("Amount mismatch detected")
            return HttpResponse(status=400)

        payment.razorpay_payment_id = razorpay_payment_id
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

        # MARK COUPON AS USED (IMPORTANT)

        if order.coupon:
            PromotionUsage.objects.get_or_create(
                user=order.user,
                promotion=order.coupon,
                order=order
            )

        logger.info(f"Payment success: {razorpay_payment_id}")

        return HttpResponse(status=200)

    return HttpResponse(status=200)


@csrf_protect
@login_required
@transaction.atomic
def verify_payment(request):
    if request.method != "POST":
        return HttpResponseBadRequest("Invalid request")

    razorpay_order_id = request.POST.get("razorpay_order_id")
    razorpay_payment_id = request.POST.get("razorpay_payment_id")
    razorpay_signature = request.POST.get("razorpay_signature")

    payment = Payment.objects.select_for_update().select_related(
        "order"
    ).filter(
        razorpay_order_id=razorpay_order_id
    ).first()

    if not payment:
        return JsonResponse({"success": False}, status=400)

    # already confirmed
    if payment.status == "SUCCESS":
        return JsonResponse({"success": True})

    client = razorpay.Client(
        auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
    )

    try:
        client.utility.verify_payment_signature({
            "razorpay_order_id": razorpay_order_id,
            "razorpay_payment_id": razorpay_payment_id,
            "razorpay_signature": razorpay_signature,
        })
    except razorpay.errors.SignatureVerificationError:
        return JsonResponse({"success": False}, status=400)

    # mark success immediately
    payment.razorpay_payment_id = razorpay_payment_id
    payment.status = "SUCCESS"
    payment.save(update_fields=["razorpay_payment_id", "status"])

    order = payment.order
    order.payment_status = "SUCCESS"
    order.status = "CONFIRMED"
    order.paid_at = timezone.now()
    order.save(update_fields=["payment_status", "status", "paid_at"])

    if order.coupon:
        PromotionUsage.objects.get_or_create(
            user=order.user,
            promotion=order.coupon,
            order=order
        )

    CartItem.objects.filter(cart__user=order.user).delete()

    return JsonResponse({"success": True})

# SUCCESS PAGE

@never_cache
@login_required
@transaction.atomic
def success(request, order_id):

    updated = Order.objects.filter(
        order_id=order_id,
        user=request.user,
        payment_status="SUCCESS",
        success_viewed=False
    ).update(success_viewed=True)

    if updated == 0:
        return redirect("order_detail", order_id=order_id)

    order = Order.objects.get(order_id=order_id)

    return render(request, "success.html", {
        "order": order
    })
