import csv
import os
import requests  # requests 라이브러리 추가
import io        # io 라이브러리 추가
from django.core.management.base import BaseCommand
from menu.models import Menu
from stores.models import Store
from markets.models import Market 

class Command(BaseCommand):
    help = 'CSV 파일에서 store_id 대신 store_name으로 메뉴 데이터를 DB에 추가합니다.'

    def handle(self, *args, **options):
        # S3 URL을 직접 지정합니다.
        csv_file_path = 'https://oyes-hackathon.s3.ap-northeast-2.amazonaws.com/store/dummy.csv' 

        try:
            # S3에서 파일을 다운로드합니다.
            response = requests.get(csv_file_path)
            response.raise_for_status()  # HTTP 오류가 발생하면 예외를 발생시킵니다.

            # 다운로드한 파일의 내용을 UTF-8로 명시적으로 디코딩하여 in-memory 파일처럼 사용합니다.
            csv_text = io.StringIO(response.content.decode('utf-8'))

            # CSV 파일에서 데이터 읽기
            reader = csv.DictReader(csv_text)
            for i, row in enumerate(reader):
                row_number = i + 1

                try:
                    # store_name과 market_id를 사용하여 Store와 Market 객체를 찾습니다.
                    store_name = row.get('store_name')
                    market_id = row.get('market_id')

                    if not store_name or not market_id:
                        self.stdout.write(self.style.ERROR(f"행 {row_number}: 'store_name' 또는 'market_id' 필드가 누락되었습니다. 해당 행을 건너뜁니다."))
                        continue

                    store_obj = Store.objects.get(store_name=store_name)
                    market_obj = Market.objects.get(market_id=market_id)

                except Store.DoesNotExist:
                    self.stdout.write(self.style.ERROR(f"행 {row_number}: '{store_name}'라는 이름의 스토어가 존재하지 않습니다. 해당 행을 건너뜁니다."))
                    continue
                except Market.DoesNotExist:
                    self.stdout.write(self.style.ERROR(f"행 {row_number}: 'market_id'가 '{market_id}'인 마켓이 존재하지 않습니다. 해당 행을 건너뜁니다."))
                    continue
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"행 {row_number}: 스토어 또는 마켓 객체 오류 - {e}. 해당 행을 건너뜁니다."))
                    continue
                
                # 한 행에서 여러 메뉴 정보를 추출하여 각각 객체 생성
                for menu_num in range(1, 4): # 최대 3개의 메뉴를 가정
                    korean_key = f'korean{menu_num}'
                    english_key = f'english{menu_num}'
                    ex_key = f'ex{menu_num}'
                    price_key = f'price{menu_num}'

                    # 필드가 존재하고 비어있지 않은지 확인
                    if all(key in row and row[key] for key in [korean_key, english_key, price_key]):
                        # Django ORM은 store=store_obj를 받으면
                        # 자동으로 store_obj의 primary key (store_id)를 Menu 모델의
                        # 외래 키 필드에 저장합니다.
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
        except requests.exceptions.RequestException as e:
            self.stdout.write(self.style.ERROR(f'오류가 발생했습니다: URL에서 파일을 가져올 수 없습니다. {e}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'오류가 발생했습니다: {e}'))

