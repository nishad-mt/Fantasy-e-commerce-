from django.shortcuts import render,redirect
from django.shortcuts import redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import WishlistModel, WishlistItem, Product

@login_required
def toggle_wishlist(request, product_id):
    if request.method == 'POST':
        product = get_object_or_404(Product, product_id=product_id)

        wishlist, _ = WishlistModel.objects.get_or_create(
            user=request.user
        )

        item = WishlistItem.objects.filter(wishlist=wishlist,product=product).first()

        if item:
            item.delete()
        else:
            WishlistItem.objects.create(
                wishlist=wishlist,
                product=product
            )

    return redirect(request.META.get('HTTP_REFERER', 'products'))

@login_required
def wishlist(request):
    if not request.user.is_authenticated:
        return redirect('login')

    items = (
        WishlistItem.objects.filter(wishlist__user=request.user)
        .select_related('product')
        .prefetch_related('product__variants', 'product__images')
    )
    return render(request, 'wishlist.html', {'items': items})