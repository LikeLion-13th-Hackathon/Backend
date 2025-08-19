from django.contrib import admin
from .models import FeedbackTag, Topic

class FeedbackTagAdmin(admin.ModelAdmin):
    list_display = ("id", "polarity", "tag")
    list_filter = ("polarity",)
    search_fields = ("tag",)
    ordering = ("polarity", "tag")

class TopicAdmin(admin.ModelAdmin):
    list_display = ("id", "category", "topic", "caption")
    list_filter = ("category",)
    search_fields = ("topic",)
    ordering = ("category", "topic")

admin.site.register(FeedbackTag, FeedbackTagAdmin)
admin.site.register(Topic, TopicAdmin)