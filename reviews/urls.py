from django.urls import path
from reviews.views import *

urlpatterns = [
    # 리스트/생성: /stores/{store_id}/reviews/
    path('', ReviewListView.as_view()),
    path('<int:review_id>/', ReviewView.as_view()),
    path('tag/', TagListView.as_view()),
]