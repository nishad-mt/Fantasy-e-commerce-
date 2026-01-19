from django.contrib import admin
from .models import Order,OrderItem

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['order_id','user','address','total_amount','delivery_date','status','payment_method','payment_status']

@admin.register(OrderItem)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['order','variant','quantity','price']
