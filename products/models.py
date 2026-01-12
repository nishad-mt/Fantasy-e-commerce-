from django.db import models
import uuid
from django.utils.text import slugify

def product_main_image_path(instance, filename):
    ext = filename.split('.')[-1]
    category_slug = instance.category.slug or "uncategorized"
    product_slug = instance.slug or uuid.uuid4().hex[:8]
    return f"products/{category_slug}/{product_slug}/main.{ext}"

def product_gallery_path(instance, filename):
    ext = filename.split('.')[-1]
    unique = uuid.uuid4().hex[:8]
    return f"products/{instance.product.category.slug}/{instance.product.slug}/gallery/{unique}.{ext}"

class Categories(models.Model):
    category_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    image = models.ImageField(upload_to="categories_image/", blank=True, null=True)
    description = models.TextField()
    is_active = models.BooleanField(default=True)
    slug = models.SlugField(unique=True, null=True)
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.name

class Product(models.Model):

    product_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    category = models.ForeignKey(Categories, on_delete=models.CASCADE, related_name="products")
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    sku = models.CharField(max_length=50, unique=True,blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    main_image = models.ImageField(upload_to=product_main_image_path)  
    best_before = models.CharField(max_length=100, blank=True, null=True)
    nutritional_info = models.CharField(max_length=500, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to=product_gallery_path)  # ✅ Dynamic!
    
    def __str__(self):
        return f"{self.product.name} Image"

class SizeVariant(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="variants")
    size_name = models.CharField(max_length=50)  
    price = models.DecimalField(max_digits=10, decimal_places=2)
    is_available = models.BooleanField(default=True) 
    
    class Meta:
        unique_together = ('product', 'size_name') 
    
    def __str__(self):
        return f"{self.product.name} - {self.size_name}"
