from rest_framework import serializers
from .models import Review, ReviewTag

SINGLE_SELECT_GROUPS = {
    ("restaurants", "Spicy Level"),
    ("snacks", "Spicy Level"),
    ("fresh", "Freshness"),
    # 필요에 따라 추가
}

class ReviewTagSerializer(serializers.ModelSerializer):
    class Meta:
        # 어떤 모델을 시리얼라이즈할 건지
        model = ReviewTag
        # 모델에서 어떤 필드를 가져올지
        # 전부 가져오고 싶을 때
        fields = "__all__"

class ReviewCreateSerializer(serializers.ModelSerializer):
    tag_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        allow_empty=True,
    )
    
    class Meta:
        model = Review
        fields = ["store", "comment", "tag_ids"]

    def validate(self, attrs):
        raw_ids = self.initial_data.get("tag_ids") or []
        if not raw_ids:
            return attrs
        
        # 중복 제거(중복 입력을 에러로 처리하려면 여기서 검사 가능)
        unique_ids = list(dict.fromkeys(raw_ids))

        # 태그 조회 + (category, group) 키 구성
        tags = list(
            ReviewTag.objects.filter(id__in=unique_ids)
            .values("id", "category", "group")
        )
        found_ids = {t["id"] for t in tags}
        missing = set(unique_ids) - found_ids
        if missing:
            raise serializers.ValidationError(
                {"tag_ids": "존재하지 않는 태그가 포함되어 있습니다."}
            )

        # 그룹별 개수 집계
        by_key = {}
        for t in tags:
            key = (t["category"], t["group"])
            by_key[key] = by_key.get(key, 0) + 1

        # 단일 선택 그룹 정책 검사
        for key, cnt in by_key.items():
            if key in SINGLE_SELECT_GROUPS and cnt > 1:
                raise serializers.ValidationError(
                    {"tag_ids": f"그룹 '{key[1]}'은(는) 단일 선택만 가능합니다."}
                )

        attrs["_resolved_tag_ids"] = unique_ids
        return attrs
    
    def create(self, validated_data):
        tag_ids = validated_data.pop("_resolved_tag_ids", [])
        request = self.context.get("request")
        review = Review.objects.create(user=getattr(request, "user", None), **validated_data)
        if tag_ids:
            review.tags.add(*tag_ids)
        return review
    
# 리뷰 읽기용
class ReviewSerializer(serializers.ModelSerializer):
    tags = ReviewTagSerializer(many=True, read_only=True)
    liked = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = [
            "id", "store", "user", "comment",
            "likes_count", "tags", "liked",
            "created", "updated"
        ]

    def get_liked(self, obj):
        request = self.context.get("request")
        if not request or not request.user or request.user.is_anonymous:
            return False
        return obj.likes.filter(user=request.user).exists()



