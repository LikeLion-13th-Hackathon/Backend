from rest_framework import serializers
from .models import Menu

class MenuSerializer(serializers.ModelSerializer):
    review_count = serializers.IntegerField()

    class Meta:
        model = Menu
        fields = '__all__'