from django.urls import path
from testapi.views import *

urlpatterns = [
    path('', health_check),
    path('upload/', ImageUploadView.as_view(), name='image-upload'),
    path('receipt/', ReceiptView.as_view()),
    path('receipt/compare/', ReceiptAddressCompareView.as_view()),
    path('store/', StoreView.as_view())
]