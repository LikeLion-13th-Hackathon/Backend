from django.db import models
from accounts.models import User

# 추상 클래스
class BaseModel(models.Model):
    created = models.DateTimeField(auto_now_add=True) # 객체를 생성할 때 날짜와 시간 저장
    updated = models.DateTimeField(auto_now=True)  # 객체를 저장할 때 날짜와 시간 갱신

    class Meta:
        abstract = True
    
class FeedbackTag(models.Model):

    id = models.AutoField(primary_key=True)

    POLARITY_CHOICES = (
        ("positive", "positive"),
        ("negative", "negative"),
        ("neutral", "neutral")
    )

    polarity = models.CharField(
        max_length=8,
        choices=POLARITY_CHOICES,
        default="positive",
    )

    tag = models.CharField(max_length=64, unique=True)
    
    def __str__(self):
        return self.tag
    
class Feedback(BaseModel):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='feedbacks')
    thumbs = models.BooleanField(default=True) # True = positive, False = negative
    comment = models.TextField(blank=True, default="", max_length=500)
    tags = models.ManyToManyField(FeedbackTag, related_name="feedbacks", blank=True)

class Topic(models.Model):
    id = models.AutoField(primary_key=True)

    CATEGORY_CHOICES = (
        ("fresh", "fresh"),
        ("snacks", "snacks"),
        ("goods", "goods"),
        ("restaurants", "restaurants")
    )

    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES
    )

    topic = models.CharField(max_length=50)
    caption = models.CharField(max_length=100, blank=True, null=True)

class Conversation(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='conversations')
    topics = models.ManyToManyField(Topic, related_name="conversations", blank=False)
    comment = models.TextField(blank=True, default="", max_length=500)