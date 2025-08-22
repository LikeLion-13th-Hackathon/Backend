import csv
import os
import boto3  # boto3 라이브러리를 추가합니다.
import io     # io 라이브러리를 추가합니다.
from django.core.management.base import BaseCommand
from menu.models import Menu
from stores.models import Store
from markets.models import Market 

class Command(BaseCommand):
    help = 'S3에서 CSV 파일을 읽어 메뉴 데이터를 DB에 추가합니다.'

    def handle(self, *args, **options):
        # 환경 변수에서 AWS 자격 증명과 S3 버킷/객체 정보를 가져옵니다.
        # 실제 배포 환경에서는 IAM Role을 사용하는 것이 더 안전합니다.
        AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
        AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
        BUCKET_NAME = 'oyes-hackathon'
        OBJECT_KEY = 'store/menu_dummy.csv'

        try:
            # boto3 클라이언트 생성
            s3_client = boto3.client(
                's3',
                aws_access_key_id=AWS_ACCESS_KEY_ID,
                aws_secret_access_key=AWS_SECRET_ACCESS_KEY
            )

            # S3에서 파일 객체 가져오기
            s3_object = s3_client.get_object(Bucket=BUCKET_NAME, Key=OBJECT_KEY)
            
            # 파일 내용을 읽어 UTF-8로 디코딩합니다. 'utf-8-sig'는 BOM을 자동으로 제거합니다.
            csv_content = s3_object['Body'].read().decode('utf-8-sig')
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'S3에서 파일을 가져오는 중 오류가 발생했습니다: {e}'))
            return

        try:
            # io.StringIO를 사용하여 파일 내용을 파일 객체처럼 다룹니다.
            reader = csv.DictReader(io.StringIO(csv_content))
            
            for i, row in enumerate(reader):
                row_number = i + 1

                try:
                    # 'store_name'과 'market_id'를 사용하여 Store와 Market 객체를 찾습니다.
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
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'오류가 발생했습니다: {e}'))
