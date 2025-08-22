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
        fields = ["id", "topic"]  # Topic에 name 필드가 있다고 가정

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

    def create(self, validated_data):
        topics = validated_data.pop("topics", [])
        user = self.context["request"].user
        conv = Conversation.objects.create(user=user, **validated_data)
        conv.topics.set(topics)
        return conv