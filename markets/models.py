from django.db import models

class Market(models.Model):
    market_id = models.AutoField(primary_key=True)
    market_name = models.CharField(max_length=40) 
    market_image = models.CharField(max_length=255, null=True, blank=True)
    market_image2 = models.CharField(max_length=255, null=True, blank=True)
    market_image3 = models.CharField(max_length=255, null=True, blank=True)
    market_english = models.CharField(max_length=40, null=True, blank=True) 

    class Meta:
        db_table = "market"
        verbose_name = "시장"
        verbose_name_plural = "시장 목록"

    def __str__(self):
        return self.market_name