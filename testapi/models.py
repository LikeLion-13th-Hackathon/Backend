from django.db import models

# 추상 클래스 정의
class BaseModel(models.Model):
    created = models.DateTimeField(auto_now_add=True) # 객체를 생성할 때 날짜와 시간 저장
    updated = models.DateTimeField(auto_now=True)  # 객체를 저장할 때 날짜와 시간 갱신

    class Meta:
        abstract = True

class Image(BaseModel):
    id = models.AutoField(primary_key=True)
    image_url = models.URLField(max_length=500)  # S3에 업로드된 이미지의 URL 저장

    def __str__(self):
        return f"Image {self.id}"
    
class Store(BaseModel):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=50)
    address = models.CharField(max_length=100)