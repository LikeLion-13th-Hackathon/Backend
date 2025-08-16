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
    
def normalize_address(addr: str) -> str:
    if not addr:
        return ""
    s = str(addr).strip()
    # 다중 공백 -> 하나
    s = " ".join(s.split())
    # 쉼표/마침표만 제거(하이픈은 유지)
    for ch in [",", "."]:
        s = s.replace(ch, " ")
    # 특별시 변환
    for token in ("서울특별시", "서울시"):
        s = s.replace(token, "서울")
    s = " ".join(s.split())
    return s

def score_pair(a: str, b: str) -> dict:
    na, nb = normalize_address(a), normalize_address(b)
    r = fuzz.ratio(na, nb)
    p = fuzz.partial_ratio(na, nb)
    return {"ratio": r, "partial": p}

def pick_better(s1: dict, s2: dict) -> tuple[dict, str]:
    # ratio 높은 쪽 우선, 동률이면 partial 높은 쪽
    if s1["ratio"] > s2["ratio"]:
        return s1, "roadname"
    if s2["ratio"] > s1["ratio"]:
        return s2, "number"
    if s1["partial"] >= s2["partial"]:
        return s1, "roadname"
    else:
        return s2, "number"

def compare_address(ocr_addr: str, roadname_addr: str | None, number_addr: str | None) -> dict:
    # 점수 계산
    road_scores = score_pair(ocr_addr, roadname_addr or "")
    num_scores  = score_pair(ocr_addr, number_addr or "")

    # 더 높은 점수로 선택
    best_scores, best_type = pick_better(road_scores, num_scores)

    # - 엄격: ratio >= 93
    # - 관대: partial >= 98 and ratio >= 85
    strict_ok = best_scores["ratio"] >= 93
    lenient_ok = (best_scores["partial"] >= 97 and best_scores["ratio"] >= 85)

    match = strict_ok or lenient_ok

    return {
        "match": match,
        "best_type": best_type, # 'roadname' or 'number'
        "best_scores": best_scores,
        "road_scores": road_scores,
        "number_scores": num_scores,
    }

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
            current_store_roadname_address = current_store.roadname_address
            current_store_number_address = current_store.number_address
        except Store.DoesNotExist:
            current_store_roadname_address = ""
            current_store_number_address = ""

        # 영수증의 가게 주소과 db의 가게 주소 비교
        cmp = compare_address(
            ocr_addr=receipt_store_address,
            roadname_addr=current_store_roadname_address,
            number_addr=current_store_number_address,
        )

        # best_type 기준으로 응답용 주소 선택
        current_store_address = current_store_roadname_address if cmp["best_type"] == "roadname" else current_store_number_address

        if not cmp["match"]:
            return Response({
                "address_match": False,
                "best_type": cmp["best_type"],
                "best_scores": cmp["best_scores"],
                "road_scores": cmp["road_scores"],
                "number_scores": cmp["number_scores"],
                "receipt_store_address": receipt_store_address,
                "current_store_address": current_store_address,
                "message": "영수증 정보와 가게 정보가 일치하지 않습니다.",
                "ocr_result": ocr_result,
            }, status=400)
        
        return Response({
            "receipt_store_name": receipt_store_name,
            "receipt_store_address": receipt_store_address,
            "receipt_date": receipt_date,
            "receipt_total_price": receipt_total_price,
            "current_store_name": current_store_name,
            "current_store_address": current_store_address,
            "best_type": cmp["best_type"],
            "address_match": True,
            "best_scores": cmp["best_scores"],
            "road_scores": cmp["road_scores"],
            "number_scores": cmp["number_scores"],
            "ocr_result": ocr_result,
        }, status=200)
    
class StoreView(APIView):
    def post(self, request):
        serializer = StoreSerializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)