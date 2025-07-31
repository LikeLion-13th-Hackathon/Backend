from django.urls import path
from testapi.views import *

urlpatterns = [
    path('test', health_check),
]