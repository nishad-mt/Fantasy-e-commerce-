from django import forms
from .models import Categories,Product

class CategoriesForm(forms.ModelForm):
    class Meta:
        model = Categories
        fields = ['name', 'slug', 'description', 'image']

    def clean_name(self):
        name = self.cleaned_data.get('name')

        qs = Categories.objects.filter(name__iexact=name)

        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise forms.ValidationError("Category name already exists")

        return name

    def clean_slug(self):
        slug = self.cleaned_data.get('slug')

        qs = Categories.objects.filter(slug=slug)

        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise forms.ValidationError("Slug already exists")

        return slug
    
class ProductsForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name','description','main_image','nutritional_info','best_before','is_active','category','sku']

