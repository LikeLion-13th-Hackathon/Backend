from django.shortcuts import render
from django.http import JsonResponse 
from django.shortcuts import get_object_or_404 

def health_check(request):
    if request.method == "GET":
        return JsonResponse({
            'status' : 200,
            'data' : "OK!"
        })