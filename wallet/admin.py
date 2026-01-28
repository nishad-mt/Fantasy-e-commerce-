from django.contrib import admin
from .models import Wallet,WalletTransaction

@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ['user','balance']

@admin.register(WalletTransaction)
class WalletAdmin(admin.ModelAdmin):
    list_display = ['wallet','order','created_at','amount','txn_type']
