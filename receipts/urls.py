from django.urls import path
from receipts.views import *

urlpatterns = [
    path('', ReceiptView.as_view()),
    path('match/', ReceiptAddressCompareView.as_view()),
]