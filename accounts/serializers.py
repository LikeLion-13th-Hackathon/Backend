from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken
from .models import User

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
    
# 로그인용 시리얼라이저
from django.contrib.auth import get_user_model

User = get_user_model()

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
