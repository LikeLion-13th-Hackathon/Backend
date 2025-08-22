from django.contrib import admin
from .models import Market

@admin.register(Market)
class MarketAdmin(admin.ModelAdmin):
    list_display = ('market_name', 'market_english', 'market_id')
    search_fields = ('market_name',)