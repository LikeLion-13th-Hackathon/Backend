from .models import Receipt
from rest_framework import serializers

class ReceiptSerializer(serializers.ModelSerializer):
    class Meta:
        model = Receipt
        fields = ["store_name", "store_address", "payment_datetime", "total_amount"]