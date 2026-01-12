from django.contrib import admin
from .models import Categories, Product, ProductImage, SizeVariant

# INLINE CLASSES FIRST (before ProductAdmin)
class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 0
    max_num = 6  
    fields = ['image']

class SizeVariantInline(admin.TabularInline):
    model = SizeVariant
    extra = 1

@admin.register(Categories)
class CategoriesAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active', 'slug']
    list_filter = ['is_active']
    search_fields = ['name']

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'is_active', 'created_at','sku']
    list_filter = ['category', 'is_active', 'created_at']
    search_fields = ['name', 'slug','sku']
    readonly_fields = ['created_at']
    inlines = [ProductImageInline, SizeVariantInline]  

@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ['product', 'image']

@admin.register(SizeVariant)
class SizeVariantAdmin(admin.ModelAdmin):
    list_display = ['product', 'size_name', 'price', 'is_available']
