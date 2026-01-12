from django.contrib import admin
from .models import CartItem,Cart

@admin.register(Cart)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ['user','created_at']
    
@admin.register(CartItem)
class WishlistItemAdmin(admin.ModelAdmin):
    list_display = ['cart','variant','added_at']