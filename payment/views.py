from django.shortcuts import render

def success(request):
    return render(request,"success.html")
