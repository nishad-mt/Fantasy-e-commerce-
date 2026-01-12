from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser,UserProfile

class CustomUserAdmin(UserAdmin):  # MUST inherit from UserAdmin
    model = CustomUser
    list_display = ('email', 'username', 'is_staff', 'is_active')
    list_filter = ( 'is_staff', 'is_active')
    search_fields = ('email', 'username')
    ordering = ('email',)
    fieldsets = (
        (None, {'fields': ('email', 'username', 'password')}),
        ('Permissions', {'fields': ( 'is_staff', 'is_active', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'joined_at')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'username', 'password1', 'password2', 'is_staff', 'is_active')}
        ),
    )
admin.site.register(CustomUser, CustomUserAdmin)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user',
                    'first_name','last_name',
                    'gender','mobile_number',)
    search_fields = ('mobile_number','user__email', 'user__username',)
    list_filter = ('gender',)

    
