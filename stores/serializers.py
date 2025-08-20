from rest_framework import serializers
from .models import Store

class StoreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Store
        fields = ['store_id', 'market', 'store_name', 'category', 'road_address', 'street_address', 'store_english','store_image']