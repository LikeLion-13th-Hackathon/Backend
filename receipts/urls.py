from django.urls import path
from receipts.views import *

urlpatterns = [
    path('', ReceiptView.as_view()),
    path('compare/', ReceiptAddressCompareView.as_view()),
]