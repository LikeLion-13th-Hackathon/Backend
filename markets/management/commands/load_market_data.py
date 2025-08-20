from django.core.management.base import BaseCommand
from markets.models import Market # 모델 경로를 올바르게 import 합니다.

class Command(BaseCommand):
    help = '시장 더미 데이터를 생성합니다.'

    def handle(self, *args, **kwargs):
        markets_data = [
            {
                "name": "흑석시장",
                "english": "Heukseok Market",
                "image": "https://oyes-hackathon.s3.ap-northeast-2.amazonaws.com/uploads/markets/heukseok.jpg"
            },
            {
                "name": "상도전통시장",
                "english": "Sangdo Traditional Market",
                "image": "https://oyes-hackathon.s3.ap-northeast-2.amazonaws.com/uploads/markets/sangdo.jpg"
            },
            {
                "name": "노량진수산시장",
                "english": "Noryangjin Fish Market",
                "image": "https://oyes-hackathon.s3.ap-northeast-2.amazonaws.com/uploads/markets/noryangjin.jpg"
            }
        ]

        for data in markets_data:
            Market.objects.get_or_create(
                market_name=data["name"],
                market_english=data["english"],
                market_image=data["image"]
            )
        
        self.stdout.write(self.style.SUCCESS('Successfully loaded market dummy data.'))