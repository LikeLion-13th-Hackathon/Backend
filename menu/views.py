from django.shortcuts import render
from rest_framework import generics
from .models import Menu
from .serializers import MenuSerializer

<<<<<<< HEAD
class MenuList(generics.ListAPIView):
    queryset = Menu.objects.all()
    serializer_class = MenuSerializer      
=======
<<<<<<< Updated upstream
# Create your views here.
=======
class MenuList(generics.ListAPIView):
    queryset = Menu.objects.all()
    serializer_class = MenuSerializer
 
>>>>>>> Stashed changes
>>>>>>> c08b445 (feat: menu full list)
