from django.urls import path
from .views import *

urlpatterns = [
    path('', StoreList.as_view(), name='StoreList'), 
    # ?market & ?category & ?sort_by 
]