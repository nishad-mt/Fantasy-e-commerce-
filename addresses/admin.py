from django.contrib import admin
from .models import Address

@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ('user','phone','street','city','pincode','state',)
    search_fields = ('user','city')

