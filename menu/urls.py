from django.urls import path
from .views import MenuList

urlpatterns = [
    # path('경로/', views.함수명, name='경로이름'),
    path('', MenuList.as_view(), name='MenuList')
]