from django.urls import path
from .views import StoreList

urlpatterns = [
    path('list/', StoreList.as_view(), name = 'StoreList')
]