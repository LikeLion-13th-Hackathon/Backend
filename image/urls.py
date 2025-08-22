# your_app/urls.py
from django.urls import path
from .views import GetPresignedUrlView

urlpatterns = [
    path('get-presigned-url/', GetPresignedUrlView.as_view(), name='get-presigned-url'),
]