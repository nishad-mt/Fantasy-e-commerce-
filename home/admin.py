from django.contrib import admin
from .models import ContactMessage,SiteContact

@admin.register(ContactMessage)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['user','name','number','category','message','status']
