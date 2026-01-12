from django.shortcuts import render
from products.models import Categories,Product


def home(request):
    category = Categories.objects.all()[:5]
    products = Product.objects.filter(is_active = True).order_by('-created_at')[:5]
    context = {
        'category':category,
        'products':products,
        
    }
    return render(request,'index.html',context)

def about(request):
    return render(request,'aboutus.html')

def contact(request):
    return render(request,'contact.html')
