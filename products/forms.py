from django import forms
from .models import Categories,Product

class CategoriesForm(forms.ModelForm):
    class Meta:
        model = Categories
        fields = ['name','image','description','is_active',]
    
class ProductsForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name','description','main_image','nutritional_info','best_before','is_active','category','sku']

