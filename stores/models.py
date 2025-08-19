from django.db import models
from markets.models import Market


class Store(models.Model):
    store_id = models.AutoField(primary_key=True)
    market = models.ForeignKey(Market, on_delete=models.CASCADE, default =None) 
    
    store_name = models.CharField(max_length=40)
    category = models.CharField(max_length=40, default=None)
    road_address = models.CharField(max_length=100, unique=True)
    street_address = models.CharField(max_length=100, unique=True)
    store_english = models.CharField(max_length=40)
    store_image = models.CharField(max_length=255, null=True, blank=True) 

    class Meta:
        db_table = "store"
        verbose_name = "가게"
        verbose_name_plural = "가게 목록"

    def __str__(self):
        return f"{self.store_name} ({self.category})"
