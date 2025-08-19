from django.urls import path
from reviews.views import *

urlpatterns = [
    path('tag/', TagListView.as_view()),
]