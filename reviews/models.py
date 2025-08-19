from django.db import models
from accounts.models import User
from stores.models import Store

class BaseModel(models.Model):
    created = models.DateTimeField(auto_now_add=True) # 객체를 생성할 때 날짜와 시간 저장
    updated = models.DateTimeField(auto_now=True)  # 객체를 저장할 때 날짜와 시간 갱신

    class Meta:
        abstract = True

class ReviewTag(models.Model):
    
    id = models.AutoField(primary_key=True)

    CATEGORY_CHOICES = (
        ("fresh", "fresh"),
        ("snacks", "snacks"),
        ("goods", "goods"),
        ("restaurants", "restaurants")
    )

    GROUP_CHOICES = (
        ("Review Tags", "Review Tags"),
        ("Dietary Restrictions", "Dietary Restrictions"),
        ("Spicy Level", "Spicy Level"),
        ("Freshness", "Freshness"),
        ("Usefulness", "Usefulness"),
        ("Portion Size", "Portion Size"),
    )

    category = models.CharField( # 대분류
        max_length=20,
        choices=CATEGORY_CHOICES
    )

    group = models.CharField(   # 중분류
        max_length=50,
        choices=GROUP_CHOICES
    ) 

    tag = models.CharField(max_length=50) # 세부 항목
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["category", "group", "tag"], name="uniq_domain_group_tag"),
        ]
        indexes = [
            models.Index(fields=["category", "group"]),
    ]

class Review(BaseModel):
    id = models.AutoField(primary_key=True)
    store = models.ForeignKey(Store, on_delete=models.CASCADE, null=True, blank=True, related_name='reviews')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviews') 
    comment = models.TextField(blank=True, default="", max_length=3000)
    likes_count = models.PositiveIntegerField(default=0)
    tags = models.ManyToManyField(ReviewTag, related_name="reviews", blank=True)
    class Meta:
        indexes = [
            models.Index(fields=["store"]),
        ]

class ReviewLike(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='review_likes')
    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name='likes')

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "review"], name="unique_user_review_like"),
        ]
        indexes = [
            models.Index(fields=["review"]),
            models.Index(fields=["user"]),
        ]


