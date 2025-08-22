from django.contrib import admin
from .models import Store

@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    list_display = ("store_id", "market_id", "store_name", "category", "road_address") # 사실 별로 필요없음
    search_fields = ("store_name", "category", "road_address")
