from django.shortcuts import render,redirect,get_object_or_404
from django.contrib.auth.decorators import login_required
from decimal import Decimal
from cart.models import Cart
from .models import Order,OrderItem

def order(request):
    return render(request,"order.html")

def checkout(request):
    return render(request,"checkout.html")

def create_from_cart(request):
    cart = get_object_or_404(Cart, user=request.user)
    items = cart.items.select_related("variant")
    
    if not items.exists():
        return redirect('cart:cart')
    
    subtotal = Decimal("0.00")
    for item in items:
        subtotal += item.variant.price*item.quantity
        
    tax = (subtotal * Decimal("0.05")).quantize(Decimal("0.01"))
    delivery = Decimal("0.00") if subtotal > 500 else Decimal("40.00")
    total = subtotal + tax + delivery

    order = Order.objects.create(
        user=request.user,
        total_amount=total,
        delivery_charge = delivery
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

    return render(request, "checkout.html", {
        "order": order,
        "items": order.items.select_related("variant", "variant__product")
    })

def order_detail(request):
    return render(request,"order_detail.html")
