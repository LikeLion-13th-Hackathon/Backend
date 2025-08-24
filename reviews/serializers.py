from rest_framework import serializers
from .models import Review, ReviewTag
from accounts.models import User
from django.db import transaction
from django.db.models import F

SINGLE_SELECT_GROUPS = {
    ("restaurants", "Spicy Level"),
    ("snacks", "Spicy Level"),
    ("snacks", "Portion Size"),
    ("fresh", "Freshness"),
    # 필요에 따라 추가
}

def validate_comment_min_length(value: str) -> str:
    if value is None or len(value.strip()) < 1:
        raise serializers.ValidationError("comment는 최소 1자 이상이어야 합니다.")
    return value

class TagValidationMixin:
    def _validate_and_resolve_tag_ids(self, initial_data):
        raw_ids = (initial_data or [])
        if not raw_ids:
            return []

        # 중복 제거
        unique_ids = list(dict.fromkeys(raw_ids))

        # 태그 존재 여부 확인 및 메타 수집
        tags = list(
            ReviewTag.objects.filter(id__in=unique_ids)
            .values("id", "category", "group")
        )
        found_ids = {t["id"] for t in tags}
        missing = set(unique_ids) - found_ids
        if missing:
            raise serializers.ValidationError({"tag_ids": "존재하지 않는 태그가 포함되어 있습니다."})

        # 그룹별 개수 집계 후 단일 선택 정책 적용
        by_key = {}
        for t in tags:
            key = (t["category"], t["group"])
            by_key[key] = by_key.get(key, 0) + 1

        for key, cnt in by_key.items():
            if key in SINGLE_SELECT_GROUPS and cnt > 1:
                raise serializers.ValidationError(
                    {"tag_ids": f"그룹 '{key[1]}'은(는) 단일 선택만 가능합니다."}
                )

        return unique_ids
    
class ReviewTagSerializer(serializers.ModelSerializer):
    class Meta:
        # 어떤 모델을 시리얼라이즈할 건지
        model = ReviewTag
        # 모델에서 어떤 필드를 가져올지
        # 전부 가져오고 싶을 때
        fields = "__all__"

class ReviewCreateSerializer(serializers.ModelSerializer, TagValidationMixin):
    comment = serializers.CharField(validators=[validate_comment_min_length])
    tag_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        allow_empty=True,
    )

    class Meta:
        model = Review
        fields = ["store", "comment", "tag_ids"]

    def validate(self, attrs):
        # store 필수
        if not attrs.get("store"):
            raise serializers.ValidationError({"store": "Store is required"})

        # 태그 검증
        raw_ids = self.initial_data.get("tag_ids") or []
        resolved = self._validate_and_resolve_tag_ids(raw_ids)
        attrs["_resolved_tag_ids"] = resolved
        attrs.pop("tag_ids", None)  # 안전장치
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        user = self.context["request"].user
        store = validated_data["store"]
        tag_ids = validated_data.pop("_resolved_tag_ids", [])

        # comment 길이 상한 방어 (최소는 validator에서 이미 확인)
        comment = validated_data.get("comment") or ""
        validated_data["comment"] = comment[:3000]

        review = Review.objects.create(
            user=user,
            **validated_data
        )

        if tag_ids:
            review.tags.add(*tag_ids)

        is_first_for_store = not Review.objects.filter(
            user=user, store=store
        ).exclude(id=review.id).exists()

        if is_first_for_store:
            u = User.objects.select_for_update().get(pk=user.user_id)
            u.visited_count = F("visited_count") + 1
            u.save(update_fields=["visited_count"])

        return review
    
class ReviewUpdateSerializer(serializers.ModelSerializer, TagValidationMixin):
    comment = serializers.CharField(validators=[validate_comment_min_length], required=True)
    tag_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        allow_empty=True,
    )

    class Meta:
        model = Review
        fields = ["comment", "tag_ids"]  # store 제외

    def validate(self, attrs):
        # 태그 검증
        if not self.partial and "comment" not in attrs:
            raise serializers.ValidationError({"comment": "comment는 필수입니다."})
        raw_ids = self.initial_data.get("tag_ids") or []
        resolved = self._validate_and_resolve_tag_ids(raw_ids)
        attrs["_resolved_tag_ids"] = resolved
        attrs.pop("tag_ids", None)  # 안전장치
        return attrs

    def update(self, instance, validated_data):
        tag_ids = validated_data.pop("_resolved_tag_ids", [])

        # comment는 validator로 최소 길이 보장됨
        instance.comment = (validated_data["comment"] or "")[:3000]
        instance.save()

        # 태그 전체 교체
        instance.tags.set(tag_ids)
        return instance
        
# 리뷰 읽기용
class ReviewSerializer(serializers.ModelSerializer):
    store_image = serializers.CharField(source="store.store_image", read_only=True)
    tags = ReviewTagSerializer(many=True, read_only=True)
    liked = serializers.SerializerMethodField()
    author = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = [
            "id", "store", "store_image", "user", "comment",
            "likes_count", "tags", "liked",
            "created", "updated",
            "author"
        ]

    def get_liked(self, obj):
        request = self.context.get("request")
        if not request or not request.user or request.user.is_anonymous:
            return False
        return obj.likes.filter(user=request.user).exists()
    
    def get_author(self, obj):
        u = getattr(obj, "user", None)
        if not u:
            return None
        return {
            "user_id": u.user_id,
            "username": u.username,
            "nickname": u.nickname,
            "profile_image": u.profile_image,
        }


