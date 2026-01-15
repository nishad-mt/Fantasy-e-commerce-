from django.shortcuts import render,redirect,get_object_or_404
from django.contrib.auth.decorators import login_required
from decimal import Decimal
from cart.models import Cart
from .models import Order,OrderItem
from addresses.models import Address
from django.contrib import messages
from datetime import date,datetime,timedelta

def order(request):
    return render(request,"order.html")

@login_required
def checkout(request):
    addresses = Address.objects.filter(user=request.user)
    default_address = addresses.filter(is_default=True).first()
    
    delivery_date = datetime.now().date() + timedelta(days=3)

    return render(request, "checkout.html", {
        "addresses": addresses,
        "default_address": default_address,
        'delivery_date':delivery_date.date()
    })

def create_from_cart(request):
    cart = get_object_or_404(Cart, user=request.user)
    items = cart.items.select_related("variant")
    
    if not items.exists():
        return redirect('cart:cart')
    
    order_items_total = Decimal("0.00")

    for item in items:
        line_total = item.variant.price * item.quantity
        order_items_total += line_total

    OrderItem.objects.create(
        order=order,
        variant=item.variant,
        quantity=item.quantity,
        price=item.variant.price  # snapshot taken now
    )
        
    delivery = Decimal("0.00") if order_items_total > 500 else Decimal("40.00")
    total = order_items_total  + delivery
    default_address = Address.objects.filter(user=request.user, is_default=True).first()
    delivery_date = date.today() + timedelta(days=3)
    if not default_address:
        return redirect("checkout")  # force user to pick/create address

    order = Order.objects.create(
        user=request.user,
        address=default_address,
        total_amount=total,
        delivery_charge=delivery,
        delivery_date=delivery_date
    )

    for item in items:
        OrderItem.objects.create(
            order=order,
            variant=item.variant,
            quantity=item.quantity,
            price=item.variant.price
        )

    return redirect("pay_order", order_id=order.order_id)

@login_required
def pay_order(request, order_id):
    order = get_object_or_404(Order, order_id=order_id, user=request.user)

    addresses = Address.objects.filter(user=request.user)
    default_address = addresses.filter(is_default=True).first()

    return render(request, "checkout.html", {
        "order": order,
        "items": order.items.select_related("variant", "variant__product"),
        "addresses": addresses,
        "default_address": default_address
    })

def order_detail(request):
    return render(request,"order_detail.html")

@login_required
def place_order(request):
    if request.method != "POST":
        return redirect("checkout")

    address_id = request.POST.get("address_id")
    address = get_object_or_404(Address, id=address_id, user=request.user)

    cart = get_object_or_404(Cart, user=request.user)
    items = cart.items.select_related("variant")

    if not items.exists():
        messages.error(request, "Your cart is empty.")
        return redirect("cart:cart")

    subtotal = sum(item.variant.price * item.quantity for item in items)
    delivery = Decimal("0.00") if subtotal > 500 else Decimal("40.00")
    total = subtotal + delivery
    delivery_date = date.today() + timedelta(days=3)

    order = Order.objects.create(
        user=request.user,
        address=address,
        total_amount=total,
        delivery_charge=delivery,
        delivery_date=delivery_date
    )

    for item in items:
        OrderItem.objects.create(
            order=order,
            variant=item.variant,
            quantity=item.quantity,
            price=item.variant.price
        )

    cart.items.all().delete()

    return redirect("pay_order", order_id=order.order_id)
