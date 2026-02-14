from django.shortcuts import render,redirect,get_object_or_404
from django.contrib.auth.decorators import login_required
from decimal import Decimal
from cart.models import Cart,CartItem
from .models import Order,OrderItem
from payments.models import Payment
from products.models import SizeVariant
from addresses.models import Address
from django.contrib import messages
from datetime import date,timedelta
from django.db import transaction
import uuid
from django.db.models import Case, When, IntegerField,Value
from django.utils import timezone
from django.http import JsonResponse
import razorpay
from django.conf import settings
from wallet.models import WalletTransaction,Wallet
from promotions.utils import calculate_best_discount


@login_required
def order(request):
    orders = (
        Order.objects
        .filter(user=request.user,
        status__in=["CONFIRMED", "PACKED", "DELIVERED", "CANCELLED"]
        )
        .prefetch_related("items__variant__product")
        .annotate(
            status_priority=Case(
                When(status="CONFIRMED", then=Value(1)),
                When(status="PACKED", then=Value(2)),
                When(status="DELIVERED", then=Value(3)),
                When(status="CANCELLED", then=Value(4)),
                default=Value(5),
                output_field=IntegerField(),
            )
        )
        .order_by("status_priority", "-created_at")
    )
    return render(request, "order.html", {
        "orders": orders,
    })
    

@login_required
@transaction.atomic
def create_from_cart(request):
    cart = get_object_or_404(Cart, user=request.user)
    items = cart.items.select_related("variant")

    if not items.exists():
        messages.warning(request, "Your cart is empty.")
        return redirect("cart:cart")

    # Get default address (optional for DRAFT, but good UX)
    default_address = Address.objects.filter(
        user=request.user,
        is_default=True,
        is_active=True
    ).first()

    # If no default address, we proceed with None for now
    # The user will be prompted to add/select an address on the checkout page

    # 2️⃣ Reuse existing DRAFT order OR create new one
    existing_drafts = Order.objects.filter(
        user=request.user,
        status="DRAFT",
        source="CART"
    ).order_by("-created_at")

    if existing_drafts.exists():
        order = existing_drafts.first()
        # Clean up duplicates if any
        if existing_drafts.count() > 1:
            existing_drafts.exclude(pk=order.pk).delete()
            
        # Update defaults if needed (e.g. if address was None before but now we have one)
        if default_address and not order.address:
            order.address = default_address
            order.save(update_fields=["address"])
    else:
        order = Order.objects.create(
            user=request.user,
            status="DRAFT",
            source="CART",
            address=default_address,
            delivery_date=date.today() + timedelta(days=3)
        )

    # 3️⃣ Clear existing items
    order.items.all().delete()
    
    # 4️⃣ Copy cart items → order items
    OrderItem.objects.bulk_create([
        OrderItem(
            order=order,
            variant=item.variant,
            quantity=item.quantity,
            price=item.variant.price
        )
        for item in items
    ])

    return redirect("pay_order", order_id=order.order_id)


@login_required
def pay_order(request, order_id):

    order = get_object_or_404(
        Order,
        order_id=order_id,
        user=request.user
    )

    # Block access based on order state
    if order.status == "CONFIRMED" and order.payment_status == "SUCCESS":
        return redirect("order_detail", order_id=order.order_id)

    if order.status == "PENDING_PAYMENT":
        return redirect("order_processing", order_id=order.order_id)

    if order.status != "DRAFT":
        return redirect("home")

    # ---------- Items ----------
    items = order.items.select_related("variant", "variant__product")

    if not items.exists():
        messages.error(request, "This order has no items.")
        return redirect("cart:cart")

    # ---------- Totals (preview only) ----------
    subtotal = sum(item.variant.price * item.quantity for item in items)
    delivery = Decimal("0.00") if subtotal > 500 else Decimal("40.00")

    try:
        discount, discount_type, applied_promo = calculate_best_discount(
            user=request.user,
            subtotal=subtotal,
            order=order
        )
    except Exception as e:
        # Fallback if discount calculation fails (e.g. due to missing address logic)
        discount = Decimal("0.00")
        discount_type = None
        applied_promo = None
        # valid to log error here if logging was set up

    preview_total = max(subtotal + delivery - discount, Decimal("0.00"))

    # ---------- Address ----------
    addresses = Address.objects.filter(user=request.user, is_active=True)
    # if not addresses.exists():
    #     messages.warning(request, "Please add a delivery address to continue.")
    #     return redirect("create_address")

    default_address = addresses.filter(is_default=True).first()

    if (not order.address or order.address not in addresses) and default_address:
        order.address = default_address
        order.save(update_fields=["address"])

    delivery_date = date.today() + timedelta(days=3)

    # Validate wallet exists or create it safely for display
    try:
        from wallet.models import Wallet
        wallet, _ = Wallet.objects.get_or_create(user=request.user)
        wallet_balance = wallet.balance
    except Exception:
        wallet_balance = Decimal("0.00")

    return render(request, "checkout.html", {
        "order": order,
        "items": items,
        "addresses": addresses,
        "default_address": default_address,
        "delivery_date": delivery_date,
        "preview_subtotal": subtotal,
        "preview_delivery": delivery,
        "preview_discount": discount,
        "preview_discount_type": discount_type,
        "preview_total": preview_total,
        "wallet_balance": wallet_balance,
    })



def order_detail(request,order_id):
    order = get_object_or_404(Order,order_id=order_id,user=request.user)
    items = order.items.select_related('variant','variant__product')
    return render(request,"order_detail.html",{
        'order':order,
        'items':items
        }
                  )


@transaction.atomic
@login_required
def place_order(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request"}, status=400)

    #  MUST fetch DRAFT order
    order = get_object_or_404(
        Order,
        order_id=request.POST.get("order_id"),
        user=request.user,
        status="DRAFT"
    )

    items = order.items.select_related("variant")
    if not items.exists():
        return JsonResponse({"status": "error", "message": "Order has no items."}, status=400)

    if not order.address:
        return JsonResponse({"status": "no_address"})

    # ---------- Recalculate totals ----------
    subtotal = sum(item.variant.price * item.quantity for item in items)
    delivery = Decimal("0.00") if subtotal > 500 else Decimal("40.00")

    discount, discount_type, applied_promo = calculate_best_discount(
        user=request.user,
        subtotal=subtotal,
        order=order
    )

    total = max(subtotal + delivery - discount, Decimal("0.00"))

    # ---------- Persist snapshot ----------
    order.order_items_total = subtotal
    order.delivery_charge = delivery
    order.discount_amount = discount
    order.discount_type = discount_type
    order.coupon = applied_promo if discount_type == "COUPON" else None
    order.total_amount = total
    order.delivery_date = date.today() + timedelta(days=3)

    payment_method = request.POST.get("payment_method")

    promo_confirmed = False  # initialize

    # COD

    if payment_method == "COD":
        order.payment_method = "COD"
        order.payment_status = "PENDING"
        order.status = "CONFIRMED"
        order.save()

        promo_confirmed = True

    # WALLET

    elif payment_method == "WALLET":
        wallet, _ = Wallet.objects.select_for_update().get_or_create(
            user=request.user, defaults={"balance": Decimal("0.00")}
        )

        if wallet.balance < total:
            return JsonResponse({"status": "wallet_insufficient"})

        wallet.balance -= total
        wallet.save()

        WalletTransaction.objects.create(
            wallet=wallet,
            order=order,
            amount=total,
            txn_type="DEBIT"
        )

        order.payment_method = "WALLET"
        order.payment_status = "SUCCESS"
        order.paid_at = timezone.now()
        order.status = "CONFIRMED"
        order.save()

        Payment.objects.create(
            user=request.user,
            order=order,
            razorpay_order_id=f"WALLET-{uuid.uuid4()}",
            razorpay_payment_id=f"WALLET-{uuid.uuid4()}",
            gateway_method="WALLET",
            amount=total,
            status="SUCCESS"
        )

        promo_confirmed = True


    # ONLINE
    elif payment_method == "ONLINE":
        order.payment_method = "ONLINE"
        order.payment_status = "PENDING"
        order.status = "PENDING_PAYMENT"

        # SAVE TOTALS BEFORE RAZORPAY
        order.order_items_total = subtotal
        order.delivery_charge = delivery
        order.discount_amount = discount
        order.discount_type = discount_type
        order.coupon = applied_promo if discount_type == "COUPON" else None
        order.total_amount = total
        order.delivery_date = date.today() + timedelta(days=3)

        order.save()

        return JsonResponse({
            "status": "online",
            "order_id": order.order_id
        })

    else:
        return JsonResponse({"status": "invalid_payment"}, status=400)

    # =================================================
    # 🔐 Lock promotion ONLY after CONFIRMATION
    # =================================================
    if promo_confirmed and applied_promo and applied_promo.one_time_per_user:
        from promotions.models import PromotionUsage
        PromotionUsage.objects.get_or_create(
            user=request.user,
            promotion=applied_promo,
            order=order
        )

    # 🧹 Clear cart ONLY after CONFIRMED
    if order.source == "CART":
        CartItem.objects.filter(cart__user=request.user).delete()

    return JsonResponse({
        "status": "success",
        "order_id": order.order_id
    })


@login_required
def select_address(request):
    if request.method != "POST":
        return redirect("cart:cart")

    address_id = request.POST.get("address_id")

    # Get active checkout (DRAFT)
    order = Order.objects.filter(
        user=request.user,
        status="DRAFT"
    ).first()

    if not order:
        messages.warning(
            request,
            "Your checkout session expired."
        )
        return redirect("cart:cart")

    address = get_object_or_404(
        Address,
        id=address_id,
        user=request.user,
        is_active=True
    )

    order.address = address
    order.save(update_fields=["address"])

    # 🔁 Return to same checkout page
    return redirect("pay_order", order_id=order.order_id)


@login_required
def order_success(request, order_id):
    order = get_object_or_404(
        Order,
        order_id=order_id,
        user=request.user
    )
    return render(request, "order_success.html", {"order": order})


def admin_order_detail(request, order_id):
    order = get_object_or_404(Order, order_id=order_id)
    items = order.items.select_related("variant", "variant__product")

    return render(
        request,
        "admin_order_detail.html",
        {
            "order": order,
            "items": items,
        },
    )


@login_required
@transaction.atomic
def cancel_order_request(request, order_id):
    order = get_object_or_404(
        Order,
        order_id=order_id,
        user=request.user
    )
    if order.status == "CANCELLED":
        messages.error(request, "Order already cancelled.")
        return redirect("order_detail", order_id=order.order_id)

    if order.status not in ["PENDING", "CONFIRMED"]:
        messages.error(request, "This order cannot be cancelled.")
        return redirect("order_detail", order_id=order.order_id)

    if request.method == "POST":
        reason = request.POST.get("cancel_reason")

        if not reason:
            messages.error(request, "Please select a cancellation reason.")
            return redirect("order_detail", order_id=order.order_id)

        
        # CANCEL ORDER
        order.status = "CANCELLED"
        order.cancel_reason = reason
        order.cancelled_at = timezone.now()

        # WALLET REFUND (ONLINE)
        if order.payment_method in ["ONLINE", "WALLET"] and order.payment_status == "SUCCESS":

            wallet, created = Wallet.objects.select_for_update().get_or_create(
                user=request.user
            )

            wallet.balance += order.total_amount
            wallet.save()

            WalletTransaction.objects.create(
                wallet=wallet,
                order=order,
                amount=order.total_amount,
                txn_type="CREDIT"
            )

            order.payment_status = "REFUNDED"

        order.save()

        messages.success(
            request,
            "Order cancelled successfully. "
            + ("Amount refunded to wallet." if order.payment_method == "ONLINE" else "")
        )

        return redirect("order_detail", order_id=order.order_id)

    return redirect("order_detail", order_id=order.order_id)

    
@login_required
@transaction.atomic
def buy_now(request, variant_id):

    if request.method != "POST":
        return redirect("home")

    # ---------- Address check ----------
    addresses = Address.objects.filter(user=request.user, is_active=True)
    # if not addresses.exists():
    #     messages.warning(request, "Please add a delivery address.")
    #     return redirect("create_address")

    default_address = addresses.filter(is_default=True).first()
    # if not default_address:
    #     messages.warning(
    #         request,
    #         "Please set a default delivery address."
    #     )
    #     return redirect("address_list")

    # ---------- Variant ----------
    variant = get_object_or_404(SizeVariant, id=variant_id)

    try:
        quantity = int(request.POST.get("quantity", 1))
        if quantity < 1:
            raise ValueError
    except ValueError:
        messages.error(request, "Invalid quantity.")
        return redirect("product_detail", slug=variant.product.slug)

    # ---------- Create or reuse DRAFT order ----------
    # ---------- Create or reuse DRAFT order ----------
    existing_drafts = Order.objects.filter(
        user=request.user,
        status="DRAFT",
        source="BUY_NOW"
    ).order_by("-created_at")

    if existing_drafts.exists():
        order = existing_drafts.first()
        # Clean up duplicates
        if existing_drafts.count() > 1:
            existing_drafts.exclude(pk=order.pk).delete()
            
        # Update address if available and currently missing
        if default_address and not order.address:
            order.address = default_address
            order.save(update_fields=["address"])
    else:
        order = Order.objects.create(
            user=request.user,
            status="DRAFT",
            source="BUY_NOW",
            address=default_address,
            delivery_date=date.today() + timedelta(days=3)
        )

    # ---------- Replace item in draft ----------
    order.items.all().delete()

    OrderItem.objects.create(
        order=order,
        variant=variant,
        quantity=quantity,
        price=variant.price
    )

    return redirect("pay_order", order_id=order.order_id)
