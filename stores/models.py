from django.db import models

# 공통 추상 클래스
class BaseModel(models.Model):
    created = models.DateTimeField(auto_now_add=True)  # 객체 최초 생성 시간
    updated = models.DateTimeField(auto_now=True)      # 객체 저장/수정 시간

    class Meta:
        abstract = True  # DB에 BaseModel 테이블이 직접 만들어지지 않음

# 가게 모델
class Store(BaseModel):
    store_id = models.AutoField(primary_key=True)  # 가게 식별자 (**)
    market_id = models.IntegerField()              # 시장 식별자 (추후 Market FK 가능)

    store_name = models.CharField(max_length=40)       # 가게명 (** max_length changed)
    category = models.CharField(max_length=40)         # 카테고리
    road_address = models.CharField(max_length=100, unique=True)   # 도로명 주소 (**)
    street_address = models.CharField(max_length=100, unique=True) # 지번 주소 (**)
    store_english = models.CharField(max_length=40)    # 가게 영문명

    class Meta: # DB 테이블명 명시 (ERD에 맞게)
        db_table = "store"   
        verbose_name = "가게"
        verbose_name_plural = "가게 목록"

    def __str__(self):
        return f"{self.store_name} ({self.category})"
