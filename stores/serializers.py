from rest_framework import serializers
from .models import Store
from reviews.serializers import ReviewSerializer
from menu.serializers import MenuSerializer


class StoreSerializer(serializers.ModelSerializer):
    review_count = serializers.IntegerField()
    most_liked_review = serializers.SerializerMethodField()
    menu_list = serializers.SerializerMethodField()

    class Meta:
        model = Store
        fields = ['store_id', 'store_name', 'store_english', 'store_image', 'review_count', 'most_liked_review', 'market_id', 'menu_list']

    def get_most_liked_review(self, obj):
        if hasattr(obj, 'most_liked_review_obj') and obj.most_liked_review_obj:
            # 리스트의 첫 번째 요소를 가져옵니다.
            most_liked = obj.most_liked_review_obj[0]
            return ReviewSerializer(most_liked).data
        return None
    
    def get_menu_list(self, obj):
        top_three_menus = obj.menu_set.all()[:3]
        
        return MenuSerializer(top_three_menus, many=True).data