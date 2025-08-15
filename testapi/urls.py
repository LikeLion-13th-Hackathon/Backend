from django.urls import path
from testapi.views import *

urlpatterns = [
    path('', health_check),
]