from django.shortcuts import render
from rest_framework import generics
from .models import Menu
from .serializers import MenuSerializer

class MenuList(generics.ListAPIView):
    serializer_class = MenuSerializer
