from django.urls import path
from reviews.views import *

urlpatterns = [
    # reviews/
    path('store/<int:store_id>/', StoreReviewListView.as_view()),
    path('user/<int:user_id>/', UserReviewListView.as_view()),
    path('<int:review_id>/', ReviewView.as_view()),
    path('<int:review_id>/like/', ReviewLikeToggleView.as_view()),
    path('tag/', TagListView.as_view()),
]
