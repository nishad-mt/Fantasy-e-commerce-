from django.shortcuts import render

def order(request):
    return render(request,"order.html")

def checkout(request):
    return render(request,"checkout.html")

def order_detail(request):
    return render(request,"order_detail.html")
