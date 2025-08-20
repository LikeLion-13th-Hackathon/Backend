from django.shortcuts import render
from rest_framework import generics
from .models import Market
from .serializers import MarketSerializer

class MarketList(generics.ListAPIView):
    queryset = Market.objects.all()
    serializer_class = MarketSerializer        