from django.shortcuts import render
from rest_framework import generics
from .models import Store
from .serializers import StoreSerializer

class StoreList(generics.ListAPIView):
    queryset = Store.objects.all()
    serializer_class = StoreSerializer     