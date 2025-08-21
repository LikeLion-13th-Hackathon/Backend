import csv
import os
from django.core.management.base import BaseCommand
from menu.models import Menu
from stores.models import Store
from markets.models import Market 

class Command(BaseCommand):
    help = 'CSV 파일에서 여러 메뉴 데이터를 DB에 추가합니다.'

    def handle(self, *args, **options):
        csv_file_path = '/Users/ziwon/Desktop/menu_dummy.csv' 

        if not os.path.exists(csv_file_path):
            self.stdout.write(self.style.ERROR(f'오류: 파일 {csv_file_path}를 찾을 수 없습니다.'))
            return

        try:
            with open(csv_file_path, mode='r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                for i, row in enumerate(reader):
                    row_number = i + 1

                    try:
                        store_obj = Store.objects.get(store_id=row['store_id'])
                        market_obj = Market.objects.get(market_id=row['market_id'])
                    except (Store.DoesNotExist, Market.DoesNotExist) as e:
                        self.stdout.write(self.style.ERROR(f"행 {row_number}: Store 또는 Market 객체 오류 - {e}. 해당 행을 건너뜁니다."))
                        continue
                    
                    # 한 행에서 여러 메뉴 정보를 추출하여 각각 객체 생성
                    for menu_num in range(1, 4): # 최대 3개의 메뉴를 가정
                        korean_key = f'korean{menu_num}'
                        english_key = f'english{menu_num}'
                        ex_key = f'ex{menu_num}'
                        price_key = f'price{menu_num}'

                        # 필드가 존재하고 비어있지 않은지 확인
                        if all(key in row and row[key] for key in [korean_key, english_key, price_key]):
                            Menu.objects.get_or_create(
                                store=store_obj,
                                market=market_obj,
                                korean=row[korean_key],
                                english=row[english_key],
                                ex=row[ex_key],
                                price=row[price_key]
                            )
                        else:
                            # 필드가 없거나 비어있으면 다음 메뉴로 넘어감
                            continue

            self.stdout.write(self.style.SUCCESS('메뉴 데이터 불러오기 성공.'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'오류가 발생했습니다: {e}'))
