from django.urls import path
from .views import *

urlpatterns = [
    path('', StoreList.as_view(), name='StoreList'), 
    # ?market & ?category & ?sort_by 
    path('<int:store_id>/', StoreDetail.as_view(), name='store-detail'),
]