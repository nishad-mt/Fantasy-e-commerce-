from django.contrib import admin
from .models import CartItem,Cart

@admin.register(Cart)
class Cartdmin(admin.ModelAdmin):
    list_display = ['user','created_at']
    
@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ['cart','quantity','variant','added_at']