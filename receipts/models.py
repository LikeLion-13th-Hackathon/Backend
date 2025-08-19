from django.db import models

# 추상 클래스 정의
class BaseModel(models.Model):
    created = models.DateTimeField(auto_now_add=True) # 객체를 생성할 때 날짜와 시간 저장
    updated = models.DateTimeField(auto_now=True)  # 객체를 저장할 때 날짜와 시간 갱신

    class Meta:
        abstract = True

class Receipt(BaseModel):
    id = models.AutoField(primary_key=True)

    # images[i] 식별 (필수: 어떤 이미지의 receipt인지 연결)
    image_uid = models.CharField(max_length=128, db_index=True)  # images[i].uid

    # receipt.result 전체(가볍게 쪼개 저장 + 원본 JSON 보관)

    payment_date = models.DateField(blank=True, null=True)  # 날짜 -> YYYY-MM-DD로 정규화한 값
    payment_time = models.TimeField(blank=True, null=True)  # 시간 -> HH:MM:SS
    payment_datetime = models.DateTimeField(blank=True, null=True, db_index=True) # 날짜 + 시간

    # storeInfo 요약
    store_name = models.CharField(max_length=255, blank=True, null=True)      # 점포 이름
    store_biz_no = models.CharField(max_length=64, blank=True, null=True)     # 사업자등록번호
    store_address = models.TextField(blank=True, null=False)                   # 점포 주소
    store_tels = models.JSONField(blank=True, null=True)                      # 점포 번호

    # 합계/금액 요약
    total_amount = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True)  # 총금액
    currency = models.CharField(max_length=8, blank=True, null=True, default="KRW")

    # 원본 보존: receipt.result 원본 그대로 저장
    receipt_result_raw = models.JSONField(blank=True, null=True)  # images[i].receipt.result 전체 JSON

    class Meta:
        indexes = [
            models.Index(fields=["image_uid"]),
            models.Index(fields=["payment_date"]),
            models.Index(fields=["store_name"]),
        ]