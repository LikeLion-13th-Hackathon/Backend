from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    # 기존 AbstractUser 필드 = username, email, password
    
    user_id = models.AutoField(primary_key=True)
    username = models.CharField(max_length=40, unique=False)
    email = models.EmailField(unique=True)
    nickname = models.CharField(max_length=40, null=False, default=None)
    age = models.PositiveIntegerField(null=False, default=0)
    nationality = models.CharField(max_length=4, null=True, blank=True)
    profile_image = models.CharField(max_length=255, null=True, blank=True)
    reward_count = models.PositiveIntegerField(default=0)
    visited_count = models.PositiveIntegerField(default=0)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    @staticmethod
    def get_user_by_username(username):
        try:
            return User.objects.get(username=username)
        except User.DoesNotExist:
            return None
