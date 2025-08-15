from django.urls import path
from testapi.views import *

urlpatterns = [
    path('', health_check),
    path('upload/', ImageUploadView.as_view(), name='image-upload'),
    path('ocr/', OcrView.as_view()),
    path('store/', StoreView.as_view())
]