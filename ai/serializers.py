from rest_framework import serializers
from .models import Feedback, Topic

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