from django.contrib import admin
from .models import ReviewTag

class ReviewTagAdmin(admin.ModelAdmin):
    list_display = ("id", "category", "group", "tag")
    list_filter = ("category",)
    search_fields = ("tag",)
    ordering = ("category", "tag")

admin.site.register(ReviewTag, ReviewTagAdmin)