from django.db import models
from markets.models import Market
from stores.models import Store

class Menu(models.Model):
    menu_id = models.AutoField(primary_key=True)

    store = models.ForeignKey(Store, on_delete=models.CASCADE)
    market = models.ForeignKey(Market, on_delete=models.CASCADE)

    korean = models.CharField(max_length = 40)
    english = models.CharField(max_length = 40)
    ex = models.CharField(max_length = 255, default=None)

    price = models.CharField(max_length = 10)

    class Meta: 
        db_table = "menu"
        verbose_name = "메뉴"
        verbose_name_plural = "메뉴 목록"

    def __str__ (self):
        return f"{self.korean} ({self.price})"
