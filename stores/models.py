from django.db import models

# 추상 클래스 정의
class BaseModel(models.Model):
    created = models.DateTimeField(auto_now_add=True) # 객체를 생성할 때 날짜와 시간 저장
    updated = models.DateTimeField(auto_now=True)  # 객체를 저장할 때 날짜와 시간 갱신

    class Meta:
        abstract = True

class Store(BaseModel):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=50)
    roadname_address = models.CharField(max_length=100)
    number_address = models.CharField(max_length=100)