from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    pass

    @staticmethod
    def get_user_by_username(username):
        try:
            return User.objects.get(username=username)
        except User.DoesNotExist:
            return None

    @staticmethod
    def get_user_by_email(email):  # 여기 수정
        try:
            return User.objects.get(email=email)
        except User.DoesNotExist:
            return None
