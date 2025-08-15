from django.shortcuts import render
from django.http import JsonResponse 
from django.shortcuts import get_object_or_404 
from django.views.decorators.http import require_http_methods 
from .models import * 
from rest_framework.views import APIView   
from rest_framework.response import Response
from rest_framework import status
from .serializers import ImageSerializer
from .serializers import StoreSerializer
from django.conf import settings
from django.utils import timezone
from rapidfuzz import fuzz
import boto3
import uuid
import json
import requests

def health_check(request):
    if request.method == "GET":
        return JsonResponse({
            'status' : 200,
            'data' : "OK!"
        })
    
def normalize_address(addr):
    # 시, 구, 군, 면, 동, 읍과 불필요한 기호 제거. 주소 정규화
    if not addr:
        return ''
    return (
        addr.replace(" ", "")
            .replace("시", "")
            .replace("구", "")
            .replace("군", "")
            .replace("읍", "")
            .replace("면", "")
            .replace("동", "")
            .replace("-", "")
            .replace(",", "")
            .replace(".", "")
    )

class ImageUploadView(APIView):
    def post(self, request):
        if 'image' not in request.FILES:
            return Response({"error": "No image file"}, status=status.HTTP_400_BAD_REQUEST)
        
        image_file = request.FILES['image']

        s3_client = boto3.client(
            "s3",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION
        )

         # S3에 파일 저장
        file_path = f"uploads/{uuid.uuid4()}_{image_file.name}"
        
        # S3에 파일 업로드
        try:
            s3_client.put_object(
                Bucket=settings.AWS_STORAGE_BUCKET_NAME,
                Key=file_path,
                Body=image_file.read(),
                ContentType=image_file.content_type,
            )
        except Exception as e:
            return Response({"error": f"S3 Upload Failed: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # 업로드된 파일의 URL 생성
        image_url = f"https://{settings.AWS_STORAGE_BUCKET_NAME}.s3.{settings.AWS_REGION}.amazonaws.com/{file_path}"

        # DB에 저장
        image_instance = Image.objects.create(image_url=image_url)
        serializer = ImageSerializer(image_instance)

        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
class OcrView(APIView):
    def post(self, request):
        image_file = request.FILES['file']

        # 네이버 OCR API 요청 준비
        url = 'https://e140deli82.apigw.ntruss.com/custom/v1/45208/063b748a49735894d8ed5ccb7d319025d142b0ce3854fafec62ee3053ba2da0d/document/receipt'
        secret = settings.X_OCR_SECRET
        message = {
            "version": "V2",
            "requestId": str(uuid.uuid4()),
            "timestamp": int(timezone.now().timestamp() * 1000),
            "images": [
                {
                    "format": "jpg", 
                    "name": image_file.name,
                }
            ]
        }

        files = {
            'file': (image_file.name, image_file, image_file.content_type),
            'message': (None, json.dumps(message), 'application/json'),
        }
        headers = {
            'X-OCR-SECRET': secret,
        }
        response = requests.post(url, headers=headers, files=files)
        ocr_result = response.json()
       
        # front에 보낼 영수증 정보
        receipt_info = ocr_result['images'][0]['receipt']['result']

        receipt_store_name = receipt_info['storeInfo']['name']['text']

        addresses = receipt_info['storeInfo'].get('addresses', [])
        if addresses and isinstance(addresses, list):
            receipt_store_address = addresses[0].get('text', '')
        else:
            receipt_store_address = ''

        receipt_date = receipt_info['paymentInfo']['date']['text']

        receipt_total_price = receipt_info['totalPrice']['price']['text']

        current_store_name = request.data.get('store_name')
        print(current_store_name)

        # 가게 이름으로 주소 가져와서 비교. 가게 이름은 영수증과 다른 경우가 많음
        try:
            current_store = Store.objects.get(name=current_store_name)
            print(current_store)
            print(current_store.name)
            print(current_store.address)
            current_store_address = current_store.address
        except Store.DoesNotExist:
            current_store_address = None

        # 주소 정규화
        norm_receipt_address = normalize_address(receipt_store_address)
        norm_db_address = normalize_address(current_store_address)
        
        # rapidfuzz로 유사도 점수 비교
        address_score = fuzz.ratio(norm_receipt_address, norm_db_address)
        address_match = address_score >= 80  # 유사도 80 이상이면 일치로 간주

        if not address_match:
            return Response({
                'address_match': False,
                'address_score': address_score,
                'message': '영수증 정보와 가게 정보가 일치하지 않습니다.'
            })
        
        return Response({
            'receipt_store_name': receipt_store_name,
            'receipt_store_address': receipt_store_address,
            'receipt_date': receipt_date,
            'receipt_total_price': receipt_total_price,
            'current_store_name': current_store_name,
            'current_store_address': current_store_address,
            'address_match': address_match,
            'address_score': address_score,
        })
    
class StoreView(APIView):
    def post(self, request):
        serializer = StoreSerializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)