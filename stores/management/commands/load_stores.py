import csv
import os
from django.core.management.base import BaseCommand
from stores.models import Store
from markets.models import Market 

class Command(BaseCommand):
    help = 'CSV 파일의 새로운 가게 데이터를 추가합니다.'

    def handle(self, *args, **options):
        # 파일 경로를 절대 경로로 직접 지정합니다.
        csv_file_path = '/Users/ziwon/Desktop/dummy.csv' 

        if not os.path.exists(csv_file_path):
            self.stdout.write(self.style.ERROR(f'오류: 파일 {csv_file_path}를 찾을 수 없습니다.'))
            return

        try:
            # CSV 파일에서 데이터 읽기
            with open(csv_file_path, mode='r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                for i, row in enumerate(reader):
                    row_number = i + 1  # 실제 행 번호 (헤더 제외)

                    try:
                        # 'market_id'가 row에 있는지 확인
                        market_id = row.get('market_id')
                        if not market_id:
                            raise ValueError("'market_id' 필드가 누락되었습니다.")

                        # 'market_id'를 사용하여 Market 객체를 가져옵니다.
                        market_obj = Market.objects.get(market_id=market_id)
                    except (Market.DoesNotExist, ValueError) as e:
                        self.stdout.write(self.style.ERROR(f"행 {row_number}: 오류 발생 - {e}. 해당 행을 건너뜁니다."))
                        continue
                    
                    # Store 모델에 맞게 필드 누락 여부 확인
                    required_fields = ['store_name', 'category', 'road_address', 'street_address', 'store_english']
                    missing_fields = [field for field in required_fields if field not in row or not row[field]]

                    if missing_fields:
                        self.stdout.write(self.style.ERROR(f"행 {row_number}: 다음 필드가 누락되었거나 비어있습니다: {', '.join(missing_fields)}. 해당 행을 건너뜁니다."))
                        continue

                    # 새로운 데이터 생성 (중복이 없을 경우에만)
                    Store.objects.get_or_create(
                        road_address=row['road_address'], # 중복 체크를 위한 식별자
                        defaults={
                            'market': market_obj,
                            'store_name': row['store_name'],
                            'category': row['category'],
                            'street_address': row['street_address'],
                            'store_english': row['store_english'],
                            'store_image': row.get('store_image', '')
                        }
                    )
            self.stdout.write(self.style.SUCCESS('가게 데이터 불러오기 성공.'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'오류가 발생했습니다: {e}'))
