from django.db import models
from django.conf import settings
from products.models import Product

class WishlistModel(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name='wishlist')
    created_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user}'s wishlist"

class WishlistItem(models.Model):
    wishlist = models.ForeignKey(WishlistModel,on_delete=models.CASCADE,related_name='items')
    product = models.ForeignKey(Product,on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('wishlist', 'product')

    def __str__(self):
        return self.product.name
