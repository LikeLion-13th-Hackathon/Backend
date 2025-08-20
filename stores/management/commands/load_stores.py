import csv
import os
from django.core.management.base import BaseCommand
from stores.models import Store
from markets.models import Market 

class Command(BaseCommand):
    help = 'CSV 파일에서 가게 데이터를 불러와 DB에 저장합니다.'

    def handle(self, *args, **options):
        # 파일 경로를 절대 경로로 직접 지정합니다.
        csv_file_path = '/Users/ziwon/Desktop/1dummy.csv' 

        if not os.path.exists(csv_file_path):
            self.stdout.write(self.style.ERROR(f'오류: 파일 {csv_file_path}를 찾을 수 없습니다.'))
            return

        try:
            with open(csv_file_path, mode='r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    try:
                        market_obj = Market.objects.get(market_id=row['market_id'])
                    except Market.DoesNotExist:
                        self.stdout.write(self.style.ERROR(f"market_id '{row['market_id']}'에 해당하는 시장이 존재하지 않습니다. 해당 행을 건너뜁니다."))
                        continue

                    Store.objects.get_or_create(
                        market=market_obj,
                        store_name=row['store_name'],
                        category=row['category'],
                        road_address=row['road_address'],
                        street_address=row['street_address'],
                        store_english=row['store_english'],
                        store_image=row['store_image']
                    )
            self.stdout.write(self.style.SUCCESS('가게 데이터 불러오기 성공.'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'오류가 발생했습니다: {e}'))