from rest_framework import serializers
from .models import Review, ReviewTag

class ReviewTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReviewTag
        fields = ["id", "category", "group", "tag"]

class ReviewSerializer(serializers.ModelSerializer):
    tags = ReviewTagSerializer(many=True, read_only=True)
    liked = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = ["id", "store", "user", "comment", "likes_count", "tags", "liked", "created", "updated"]

    def get_liked(self, obj):
        # 요청 유저가 이 리뷰를 좋아요했는지 여부
        request = self.context.get("request")
        if not request or not request.user or request.user.is_anonymous:
            return False
        return obj.likes.filter(user=request.user).exists()

class ReviewTagSerializer(serializers.ModelSerializer):
    class Meta:
        # 어떤 모델을 시리얼라이즈할 건지
        model = ReviewTag
        # 모델에서 어떤 필드를 가져올지
        # 전부 가져오고 싶을 때
        fields = "__all__"
