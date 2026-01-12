from django.shortcuts import render,redirect
from .forms import CategoriesForm,ProductsForm
from django.shortcuts import get_object_or_404
from .models import Categories,Product,SizeVariant,ProductImage
from wishlist.models import WishlistItem,WishlistModel
from cart.models import Cart,CartItem
from django.utils.safestring import mark_safe
from django.contrib.auth.decorators import login_required
from django.contrib import messages
import json
from django.views.decorators.cache import never_cache
from django.contrib.auth import get_user_model
from accounts.decarators import admin_required
from django.db.models import Min, Q
from decimal import Decimal

User = get_user_model()

def products(request, slug=None):
    cats = Categories.objects.all()
    selected_category = None

    products = Product.objects.all().annotate(
        min_price=Min('variants__price')
    )

    # Wishlist
    wishlist_product_ids = []
    if request.user.is_authenticated:
        wishlist = WishlistModel.objects.filter(user=request.user).first()
        if wishlist:
            wishlist_product_ids = list(
                WishlistItem.objects.filter(wishlist=wishlist)
                .values_list('product__product_id', flat=True)
            )
    
    if slug:
        selected_category = get_object_or_404(Categories, slug=slug)
        products = products.filter(category=selected_category)
    
    query = request.GET.get('q')
    if query:
        products = products.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query)
        )

    # Price filter (VARIANT BASED)
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')

    if min_price:
        products = products.filter(min_price__gte=min_price)
    if max_price:
        products = products.filter(min_price__lte=max_price)

    # Sorting
    sort = request.GET.get('sort')
    if sort == 'price_low':
        products = products.order_by('min_price')
    elif sort == 'price_high':
        products = products.order_by('-min_price')
    elif sort == 'newest':
        products = products.order_by('-created_at')

    context = {
        'products': products,
        'category': cats,
        'sort': sort,
        'selected_category': selected_category,
        'query': query,
        'wishlist_product_ids': wishlist_product_ids,
    }

    return render(request, 'products.html', context)

@never_cache
@login_required
@admin_required
def add_products(request):
    ctgry = Categories.objects.all()
    
    if request.method == "POST":

        form = ProductsForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save()

            # Save size variants
            size_names = request.POST.getlist("size_name[]")
            size_prices = request.POST.getlist("size_price[]")
            for i, name in enumerate(size_names):
                if i < len(size_prices) and name.strip():
                    SizeVariant.objects.create(
                        product=product,
                        size_name=name.strip(),
                        price=Decimal(size_prices[i]),
                        is_available=True
                    )

            # Save multiple images properly
            images = request.FILES.getlist("gallery_images[]")   
            for img in images:
                ProductImage.objects.create(product=product, image=img)

            return redirect('admin_products')   
        return render(request, "add_products.html", {
            'form': form,
            'categories': ctgry,
            "is_edit_mode": bool(form.instance.pk),
            "main_image_url": form.instance.main_image.url if form.instance.pk and form.instance.main_image else "",
        })

    form = ProductsForm()
    return render(request, "add_products.html", {'form': form, 'categories': ctgry})

@never_cache
@login_required
@admin_required
def del_product(request,product_id):
    product = get_object_or_404(Product,pk = product_id)
    product.delete()
    return redirect('admin_products')
    
@never_cache
@login_required
@admin_required
def edit_product(request, slug):
    product = get_object_or_404(Product, slug=slug)
    categories = Categories.objects.all()

    if request.method == 'POST':
        form = ProductsForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            updated_product = form.save()

            # 1️⃣ Delete selected gallery images
            deleted_images = request.POST.getlist('deleted_gallery_images[]')
            for img_id in deleted_images:
                ProductImage.objects.filter(id=img_id, product=updated_product).delete()

            # 2️⃣ ✅ SAVE NEW GALLERY IMAGES
            new_images = request.FILES.getlist("gallery_images[]")
            for img in new_images:
                ProductImage.objects.create(
                    product=updated_product,
                    image=img
                )

            # 3️⃣ Remove old size variants
            SizeVariant.objects.filter(product=updated_product).delete()

            # 4️⃣ Recreate variants
            names = request.POST.getlist("size_name[]")
            prices = request.POST.getlist("size_price[]")
            available = request.POST.getlist("size_available[]")

            for i in range(len(names)):
                SizeVariant.objects.create(
                    product=updated_product,
                    size_name=names[i],
                    price=Decimal(prices[i]),
                    is_available=str(i) in available
                )

            messages.success(request, "Product updated!")
            return redirect("admin_products")
    else:
        form = ProductsForm(instance=product)

    # Serialize existing variants for JS
    sizes_json = mark_safe(json.dumps([
        {"name": v.size_name, "price": str(v.price), "available": v.is_available}
        for v in product.variants.all()
    ]))
    # CORRECT - use your actual ProductImage model
    gallery_images = []
    product_images = ProductImage.objects.filter(product=product)
    for img in product_images:
        gallery_images.append({
            'url': img.image.url,  # Confirm your ImageField name
            'id': img.id
        })

    
    return render(request, "add_products.html", {
        "form": form,
        "categories": categories,
        "sizes_json": sizes_json,
        "gallery_images_json": mark_safe(json.dumps(gallery_images)),
    })

@never_cache
@login_required
@admin_required
def product_detail(request, slug):
    product = get_object_or_404(Product, slug=slug)
    images = product.images.all()     # <-- retrieve all multiple images
    
    return render(request, "product_detail.html", {
        "product": product,
        "images": images
    })   

def user_product_details(request, slug):
    product = get_object_or_404(Product, slug=slug)
    latest_products = Product.objects.filter(is_active=True).annotate(starting_price=Min('variants__price')).order_by('-created_at')[:5]
    images = product.images.all()
    variants = product.variants.filter(is_available=True).order_by('price')
    initial_variant = variants.first() 

    wishlist_product_ids = []
    cart_variant_ids = []

    if request.user.is_authenticated:
        wishlist = WishlistModel.objects.filter(user=request.user).first()
        if wishlist:
            wishlist_product_ids = list(
                WishlistItem.objects.filter(wishlist=wishlist)
                .values_list('product__product_id', flat=True)
            )

        cart = Cart.objects.filter(user=request.user).first()
        if cart:
            cart_variant_ids = list(
                cart.items.values_list('variant_id', flat=True)
            )

    context = {
        "product": product,
        "images": images,
        "variants": variants,
        'initial_variant':initial_variant,
        "has_variants": variants.exists(),
        "wishlist_product_ids": wishlist_product_ids,
        "cart_variant_ids": cart_variant_ids,
        'latest_products':latest_products,
    }

    return render(request, "user_product_detail.html", context)

@never_cache
@login_required 
@admin_required
def add_category(request):
    if request.method == "POST":
        form = CategoriesForm(request.POST,request.FILES)
        if form.is_valid():
            form.save()
            return redirect('categories')
        else:
            print("FORM ERRORS:", form.errors)   
    else:    
        form = CategoriesForm()
    return render(request,"add_category.html",{'form':form})

@never_cache
@login_required 
@admin_required       
def edit_category(request,category_id):
    category = get_object_or_404(Categories, pk=category_id)

    if request.method == "POST":
        form = CategoriesForm(request.POST,request.FILES,instance=category)
        if form.is_valid():
            cat = form.save(commit=False)
            if category.is_active and not cat.is_active:
                Product.objects.filter(category=category).update(is_active=False)
            cat.save()
            return redirect('categories')
    else:    
        form = CategoriesForm(instance=category)
    return render(request,"add_category.html",{
        'form':form,
        'is_edit': True,
    })

def product_review(request):
    return render(request,'product_review.html')

@never_cache
@login_required
@admin_required
def del_category(request,category_id):
    category = get_object_or_404(Categories, pk=category_id)
    category.delete()
    return redirect("categories")