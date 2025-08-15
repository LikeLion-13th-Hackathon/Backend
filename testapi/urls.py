from django.urls import path
from testapi.views import *

urlpatterns = [
    path('', health_check),
    path('upload/', ImageUploadView.as_view(), name='image-upload')
]