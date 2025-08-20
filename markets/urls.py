from django.urls import path
from .views import MarketList

urlpatterns = [
    # path('경로/', views.함수명, name='경로이름'),
    path('list/', MarketList.as_view(), name = 'MarketList')
]