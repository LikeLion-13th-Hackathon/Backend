import csv
import os
from django.core.management.base import BaseCommand
from stores.models import Store
from markets.models import Market # Market 모델도 import 합니다.

class Command(BaseCommand):
    help = 'CSV 파일에서 가게 데이터를 불러와 DB에 저장합니다.'

    def handle(self, *args, **options):
        csv_file_path = os.path.join('stores', 'store_data.csv') 

        try:
            with open(csv_file_path, mode='r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    # market_id로 Market 객체를 가져옵니다.
                    market_obj = Market.objects.get(market_id=row['market_id'])

                    Store.objects.get_or_create(
                        market=market_obj, # 가져온 Market 객체를 할당합니다.
                        store_name=row['store_name'],
                        category=row['category'],
                        road_address=row['road_address'],
                        street_address=row['street_address'],
                        store_english=row['store_english'],
                        store_image=row['store_image']
                    )
            self.stdout.write(self.style.SUCCESS('가게 데이터 불러오기 성공.'))
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f'오류: 파일 {csv_file_path}를 찾을 수 없습니다.'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'오류가 발생했습니다: {e}'))