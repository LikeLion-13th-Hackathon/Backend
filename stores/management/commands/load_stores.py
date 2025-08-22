import csv
import os
import boto3
import io
from django.core.management.base import BaseCommand
from stores.models import Store
from markets.models import Market

class Command(BaseCommand):
    help = 'S3에서 CSV 파일을 읽어 가게 데이터를 DB에 추가합니다.'

    def handle(self, *args, **options):
        # S3 연결 정보를 환경 변수 또는 직접 설정합니다.
        AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
        AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
        BUCKET_NAME = 'oyes-hackathon'  # 실제 S3 버킷 이름으로 변경
        OBJECT_KEY = 'store/dummy.csv' # S3에 저장된 파일 경로 (예: dummy/store_dummy.csv)

        # boto3 클라이언트 생성
        try:
            s3_client = boto3.client(
                's3',
                aws_access_key_id=AWS_ACCESS_KEY_ID,
                aws_secret_access_key=AWS_SECRET_ACCESS_KEY
            )

            # S3에서 파일 객체 가져오기
            s3_object = s3_client.get_object(Bucket=BUCKET_NAME, Key=OBJECT_KEY)
            csv_content = s3_object['Body'].read().decode('utf-8-sig')
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'S3에서 파일을 가져오는 중 오류가 발생했습니다: {e}'))
            return

        try:
            # io.StringIO를 사용하여 파일 객체를 파일처럼 다룹니다.
            reader = csv.DictReader(io.StringIO(csv_content))
            
            for i, row in enumerate(reader):
                row_number = i + 1

                try:
                    market_id = row.get('market_id')
                    if not market_id:
                        raise ValueError("'market_id' 필드가 누락되었습니다.")
                    
                    market_obj = Market.objects.get(market_id=market_id)
                except (Market.DoesNotExist, ValueError) as e:
                    self.stdout.write(self.style.ERROR(f"행 {row_number}: 오류 발생 - {e}. 해당 행을 건너뜁니다."))
                    continue
                
                required_fields = ['store_name', 'category', 'road_address', 'street_address', 'store_english']
                missing_fields = [field for field in required_fields if field not in row or not row[field]]

                if missing_fields:
                    self.stdout.write(self.style.ERROR(f"행 {row_number}: 다음 필드가 누락되었거나 비어있습니다: {', '.join(missing_fields)}. 해당 행을 건너뜁니다."))
                    continue

                Store.objects.get_or_create(
                    road_address=row['road_address'],
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

