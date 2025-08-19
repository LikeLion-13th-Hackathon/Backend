from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    # AbstractUser의 기본 필드(username, email, password 등)를 재정의하지 않습니다.
    # 단, unique 속성을 변경하려는 email, username은 재정의합니다.
    
    user_id = models.AutoField(primary_key=True)
    
    # 1. username 필드: AbstractUser에도 있지만 unique=False로 재정의
    username = models.CharField(max_length=40, unique=False)
    
    # 2. email 필드: AbstractUser의 email 필드에 unique=True 속성 추가
    email = models.EmailField(unique=True)
    
    # 3. nickname 필드: null=False와 default=None의 충돌을 피하기 위해 default=''로 변경
    nickname = models.CharField(max_length=40, null=False, default='')
    
    age = models.PositiveIntegerField(null=False, default=0)
    nationality = models.CharField(max_length=4, null=True, blank=True)
    profile_image = models.CharField(max_length=255, null=True, blank=True)
    reward_count = models.PositiveIntegerField(default=0)
    visited_count = models.PositiveIntegerField(default=0)

    # 이메일을 로그인 ID로 사용하도록 설정
    USERNAME_FIELD = 'email'
    # username은 필수 입력 필드로 설정
    REQUIRED_FIELDS = ['username']

    @staticmethod
    def get_user_by_username(username):
        try:
            return User.objects.get(username=username)
        except User.DoesNotExist:
            return None