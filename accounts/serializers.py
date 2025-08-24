from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken
from .models import User, RewardHistory
from reviews.models import Review

from django.contrib.auth import get_user_model

User = get_user_model()

# 이메일 중복/형식만 검사하는 전용 시리얼라이저
class EmailCheckSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("이미 사용 중인 이메일입니다.")
        return value


# 회원가입용 시리얼라이저
class RegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'username', 'email', 'password',
            'nickname', 'age', 'nationality', 'profile_image'
        ]

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user

    # 이메일 유효성 검사 함수
    def validate_email(self, value):
        
        # 이메일 형식이 맞는지 검사
        if not "@" in value:
            raise serializers.ValidationError("Invalid email format")
        
        # 이메일 중복 여부 검사
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already exists.")
        
        return value

class AuthSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        email = data.get("email")
        password = data.get("password")

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise serializers.ValidationError("User not found")

        if not user.check_password(password):
            raise serializers.ValidationError("Incorrect email or password")

        data["user"] = user
        return data

class UserSerializer(serializers.ModelSerializer):
    visited_count = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "user_id", "email", "username", "nickname",
            "age", "nationality", "profile_image",
            "reward_count", "visited_count",
        ]

    def get_visited_count(self, obj):
        # 유저가 리뷰를 남긴 상점의 "서로 다른" 개수
        return (
            Review.objects
            .filter(user=obj)
            .values("store_id")
            .distinct()
            .count()
        )
    
class RewardChangeSerializer(serializers.Serializer):
    delta = serializers.IntegerField()  # 음수/양수 모두 허용
    caption = serializers.CharField(max_length=100, allow_blank=False)

    def validate_delta(self, value):
        if value == 0:
            raise serializers.ValidationError("delta는 0이 아니어야 합니다.")
        return value
    
    def validate_caption(self, value: str):
        if value is None:
            raise serializers.ValidationError("caption은 필수입니다.")
        # 공백만 있는 경우 금지
        if value.strip() == "":
            raise serializers.ValidationError("caption은 비어 있을 수 없습니다.")
        return value.strip()
    
class RewardHistoryReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = RewardHistory
        fields = ("id", "caption", "point", "balance", "created")

class PublicUserSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = [
            "user_id",
            "nickname",
            "profile_image"
        ]
