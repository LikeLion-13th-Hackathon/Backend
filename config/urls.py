from django.contrib import admin
from django.urls import path, include
from testapi.views import *
from accounts.views import *
from receipts.views import *
from stores.views import *
from markets.views import *
from menu.views import *

urlpatterns = [
    path('admin/', admin.site.urls),
    path('test/', include('testapi.urls')),
    path('account/', include('accounts.urls')),
    path('receipt/', include('receipts.urls')),
    path('store/', include('stores.urls')),
    path('market/', include('markets.urls')),
    path('menu/', include('menu.urls'))
]