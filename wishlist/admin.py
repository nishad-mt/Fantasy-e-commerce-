from django.contrib import admin
from .models import WishlistItem,WishlistModel

@admin.register(WishlistModel)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ['user','created_at']
    
@admin.register(WishlistItem)
class WishlistItemAdmin(admin.ModelAdmin):
    list_display = ['wishlist','product','added_at']