from .models import Categories, Product

def sync_category_status(category):
    has_active_products = Product.objects.filter(
        category=category,
        is_active=True
    ).exists()

    # If no active products → turn off category
    if not has_active_products and category.is_active:
        category.is_active = False
        category.save(update_fields=["is_active"])

    # If products exist and category was off → turn it on
    elif has_active_products and not category.is_active:
        category.is_active = True
        category.save(update_fields=["is_active"])
