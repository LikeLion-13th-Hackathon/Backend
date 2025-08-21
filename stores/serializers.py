from rest_framework import serializers
from .models import Store
from reviews.serializers import ReviewSerializer

class StoreSerializer(serializers.ModelSerializer):
    review_count = serializers.IntegerField()
    most_liked_review = serializers.SerializerMethodField()


    class Meta:
        model = Store
        fields = ['store_id', 'store_name', 'store_english', 'review_count', 'most_liked_review', 'market_id']

    def get_most_liked_review(self, obj):
        if hasattr(obj, 'most_liked_review_obj') and obj.most_liked_review_obj:
            # 리스트의 첫 번째 요소를 가져옵니다.
            most_liked = obj.most_liked_review_obj[0]
            return ReviewSerializer(most_liked).data
        return None
