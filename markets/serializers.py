from rest_framework import serializers
from .models import Market

class MarketSerializer(serializers.ModelSerializer):
    class Meta:
        model = Market
        fields = ['market_id','market_name', 'market_english', 'market_image']