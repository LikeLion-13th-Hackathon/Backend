from rest_framework import serializers
from .models import Feedback, Topic

class ChatRequestSerializer(serializers.Serializer):
    message = serializers.CharField()

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