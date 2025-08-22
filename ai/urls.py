from django.urls import path
from ai.views import *

urlpatterns = [
    path('chat/', AiChatView.as_view()),
    path('feedback/', FeedbackView.as_view()),
    path('topics/', TopicListView.as_view())
]