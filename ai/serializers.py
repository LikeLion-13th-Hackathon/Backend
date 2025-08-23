from rest_framework import serializers
from .models import Feedback, Topic, Conversation

class ChatRequestSerializer(serializers.Serializer):
    thread_id = serializers.CharField(max_length=64, allow_blank=False)
    category = serializers.ChoiceField(
        choices=("fresh", "snacks", "goods", "restaurants"),
    )
    topic = serializers.CharField(max_length=100,allow_blank=False)
    retry = serializers.BooleanField()
    role = serializers.ChoiceField(choices=("store", "user"))
    message = serializers.CharField(allow_blank=False)

    def validate_thread_id(self, v: str) -> str:
        v = v.strip()
        if not v:
            raise serializers.ValidationError("thread_id는 비어 있을 수 없습니다.")
        return v
                                              
    def validate_topic(self, v: str) -> str:
        v = v.strip()
        if not v:
            raise serializers.ValidationError("topic은 비어 있을 수 없습니다.")
        return v

    def validate_message(self, v: str) -> str:
        v = v.strip()
        if not v:
            raise serializers.ValidationError("message는 비어 있을 수 없습니다.")
        return v

class FeedbackClassifySerializer(serializers.Serializer):
    thumbs = serializers.BooleanField(required=True)
    comment = serializers.CharField(required=False, allow_blank=True, max_length=500)

# Meta 쓸 땐 ModelSerializer
class TopicSerializer(serializers.ModelSerializer):
      class Meta:
        # 어떤 모델을 시리얼라이즈할 건지
        model = Topic
        # 모델에서 어떤 필드를 가져올지
        # 전부 가져오고 싶을 때
        fields = "__all__"

class TopicMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = Topic
        fields = ["id", "topic", "category"] 

class ConversationSerializer(serializers.ModelSerializer):
    # 토픽 id 리스트로 입출력
    topics = serializers.PrimaryKeyRelatedField(
        queryset=Topic.objects.all(),
        many=True
    )

    topics_detail = TopicMiniSerializer(source="topics", many=True, read_only=True)

    class Meta:
        model = Conversation
        fields = ["id", "topics", "topics_detail", "comment"]

    
    def validate_topics(self, value):
        if not value:
            raise serializers.ValidationError("topics는 최소 1개 이상이어야 합니다.")
        return value
    
    def validate(self, attrs):
        topics = attrs.get("topics", [])
        if topics:
            cat_set = {t.category for t in topics}
            if None in cat_set or "" in cat_set:
                raise serializers.ValidationError({"topics": "선택한 topic 중 category가 비어있는 항목이 있습니다."})
            if len(cat_set) > 1:
                raise serializers.ValidationError({"topics": f"선택한 topics의 카테고리가 서로 다릅니다: {', '.join(sorted(cat_set))}"})
            # 단일 카테고리 값을 임시로 저장해 create에서 사용
            attrs["_resolved_category"] = next(iter(cat_set))
        return attrs


    def create(self, validated_data):
        topics = validated_data.pop("topics", [])
        user = self.context["request"].user
        resolved_category = validated_data.pop("_resolved_category", None)
        conv = Conversation.objects.create(
            user=user,
            category=resolved_category,  # Conversation.category 설정
            **validated_data
        )
        conv.topics.set(topics)
        return conv