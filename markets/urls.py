from django.urls import path
from .views import MarketList

urlpatterns = [
    path('list/', MarketList.as_view(), name = 'MarketList')
]