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
from .serializers import ReceiptSerializer
from django.conf import settings
from django.utils import timezone
from rapidfuzz import fuzz
from datetime import datetime as _dt, date as _date, time as _time
import boto3
import uuid
import json
import requests
import logging

logger = logging.getLogger(__name__)

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

def safe_get(d, *path, default=None):
    cur = d
    for p in path:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(p)
        if cur is None:
            return default
    return cur

def parse_date(date_obj):
    """
    입력: OCR의 paymentInfo.date 오브젝트(dict)
    출력: datetime.date 또는 None
    """
    fmt = (date_obj or {}).get("formatted") or {}
    y, m, d = fmt.get("year"), fmt.get("month"), fmt.get("day")
    if y and m and d:
        try:
            # 날짜는 반드시 date 객체로
            return _date(int(y), int(m), int(d))
        except Exception:
            pass

    # 폴백: "YYYY-MM-DD" 문자열
    text = (date_obj or {}).get("text")
    if text:
        s = str(text).strip()
        for fmt_str in ("%Y-%m-%d", "%Y.%m.%d", "%Y/%m/%d"):
            try:
                return _dt.strptime(s, fmt_str).date()
            except Exception:
                continue
    return None


def parse_time(time_obj):
    """
    입력: OCR의 paymentInfo.time 오브젝트(dict)
    출력: datetime.time 또는 None
    """
    fmt = (time_obj or {}).get("formatted") or {}
    hh, mm, ss = fmt.get("hour"), fmt.get("minute"), fmt.get("second")
    if hh and mm and ss:
        try:
            # "HH:MM:SS"로 파싱하여 time 객체 반환
            return _dt.strptime(f"{str(hh).zfill(2)}:{str(mm).zfill(2)}:{str(ss).zfill(2)}", "%H:%M:%S").time()
        except Exception:
            pass

    # 폴백: "18: 59: 29"처럼 공백 포함 형태
    text = (time_obj or {}).get("text")
    if text:
        import re
        cleaned = re.sub(r"\s+", "", str(text))  # "18: 59: 29" -> "18:59:29"
        for fmt_str in ("%H:%M:%S",):
            try:
                return _dt.strptime(cleaned, fmt_str).time()
            except Exception:
                continue
    return None

def parse_number(value):
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip()
    if not s:
        return None
    neg = False
    if s.startswith("(") and s.endswith(")"):
        neg = True
        s = s[1:-1]
    for sym in [" ", ",", "KRW", "₩", "원", "$", "USD"]:
        s = s.replace(sym, "")
    try:
        num = float(s)
        return -num if neg else num
    except Exception:
        return None
    
class ReceiptView(APIView):
    def post(self, request):
        # 1) 이미지 파일 받기
        image_file = request.FILES.get("file")
        if not image_file:
            return Response({"detail": "file 필드로 이미지를 업로드하세요."}, status=400)

        # 2) 네이버 OCR 호출

        OCR_URL = "https://e140deli82.apigw.ntruss.com/custom/v1/45208/063b748a49735894d8ed5ccb7d319025d142b0ce3854fafec62ee3053ba2da0d/document/receipt"

        message = {
            "version": "V2",
            "requestId": str(uuid.uuid4()),
            "timestamp": int(timezone.now().timestamp() * 1000),
            "images": [{"format": "jpg", "name": image_file.name}],
        }
        files = {
            "file": (image_file.name, image_file, getattr(image_file, "content_type", "image/jpeg")),
            "message": (None, json.dumps(message), "application/json"),
        }
        headers = {"X-OCR-SECRET": settings.X_OCR_SECRET}

        try:
            res = requests.post(OCR_URL, headers=headers, files=files, timeout=30)
            res.raise_for_status()
            ocr = res.json()
        except Exception as e:
            return Response({"detail": f"OCR 호출 실패: {e}"}, status=502)

        # 3) OCR 응답에서 images[].receipt만 저장
        images = ocr.get("images") or []
        if not images:
            return Response({"detail": "OCR 응답에 images가 없습니다.", "ocr": ocr}, status=200)

        saved = []
        skipped = []

        for img in images:
            image_uid = img.get("uid")
            receipt = img.get("receipt") or {}
            if not image_uid or not receipt:
                skipped.append({"image_uid": image_uid, "reason": "NO_RECEIPT_OR_UID"})
                continue

            result = receipt.get("result") or {}

            # payment
            payment_info = result.get("paymentInfo") or {}
            payment_date = parse_date(payment_info.get("date"))
            payment_time = parse_time(payment_info.get("time"))

            # store
            store_info = result.get("storeInfo") or {}
            store_name = safe_get(store_info, "name", "formatted", "value") or safe_get(store_info, "name", "text")
            store_biz_no = safe_get(store_info, "bizNum", "formatted", "value") or safe_get(store_info, "bizNum", "text")

            store_address = None
            addrs = store_info.get("addresses") or []
            if addrs:
                first = addrs[0] or {}
                store_address = safe_get(first, "formatted", "value") or first.get("text")
            
            # 주소 필수 검증: 없으면 즉시 실패 반환
            if not store_address or not str(store_address).strip():
                skipped.append({"image_uid": image_uid, "reason": "NO_ADDRESS"})
                return Response(
                    {
                        "detail": "영수증에서 주소를 추출하지 못했습니다.",
                        "image_uid": image_uid,
                        "skipped": skipped,
                    },
                    status=400,
                )
        
            tel_values = []
            for t in store_info.get("tel") or []:
                v = safe_get(t, "formatted", "value") or t.get("text")
                if v:
                    tel_values.append(v)

            # totals
            total_amount = parse_number(
                safe_get(result, "totalPrice", "price", "formatted", "value")
                or safe_get(result, "totalPrice", "price", "text")
            )

            # 헤더 저장
            row = Receipt.objects.create(
                image_uid=image_uid,
                payment_date=payment_date,
                payment_time=payment_time,
                store_name=store_name,
                store_biz_no=store_biz_no,
                store_address=store_address,
                store_tels=tel_values or None,
                total_amount=total_amount,
                currency="KRW",
                receipt_result_raw=result or None,
            )

        # 모델에 payment_datetime 필드가 있다면 결합 저장
        if hasattr(row, "payment_datetime") and row.payment_date and row.payment_time:
            try:
                # 타입이 맞는지 한 번 더  확인
                pd = row.payment_date
                pt = row.payment_time

                # 혹시 실수로 datetime이 들어왔다면 date로 보정
                if isinstance(pd, _dt):
                    pd = pd.date()
                # 혹시 문자열로 들어왔다면(비정상), 파싱하거나 건너뜀
                if not isinstance(pd, _date):
                    raise TypeError(f"payment_date must be date, got: {type(pd)}")

                # time은 datetime.time 여야 함. 문자열 등은 거부
                if not isinstance(pt, _time):
                    raise TypeError(f"payment_time must be time, got: {type(pt)}")

                row.payment_datetime = _dt.combine(pd, pt)
                row.save(update_fields=["payment_datetime"])
            except Exception as e:
                logger.warning("Failed to combine payment_datetime: %s", e)

        saved.append(row)
        resp_saved = ReceiptSerializer(saved, many=True).data
        return Response({"saved": resp_saved, "skipped": skipped}, status=status.HTTP_201_CREATED if saved else status.HTTP_200_OK)
    
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
    # - 관대: partial >= 97 and ratio >= 85
    strict_ok = best_scores["ratio"] >= 93
    lenient_ok = (best_scores["partial"] >= 97 and best_scores["ratio"] >= 85)

    match = bool(strict_ok or lenient_ok)

    return {
        "match": match,
        "best_type": best_type, # 'roadname' or 'number'
        "best_scores": best_scores,
        "road_scores": road_scores,
        "number_scores": num_scores,
    }


class ReceiptAddressCompareView(APIView):
    def post(self, request):

        image_uid = request.data.get("image_uid")
        receipt_id = request.data.get("receipt_id")
        store_id = request.data.get("store_id")

        if not (image_uid or receipt_id):
            return Response({"detail": "image_uid 또는 receipt_id 중 하나는 필수입니다."}, status=400)
       
        # 1) 영수증 조회 (image_uid가 있으면 최신 1건, 없으면 receipt_id로 단건)
        try:
            if receipt_id:
                receipt = Receipt.objects.get(id=receipt_id)
            else:
                receipt = Receipt.objects.filter(image_uid=image_uid).order_by("-id").first()
                if not receipt:
                    return Response({"detail": f"image_uid={image_uid} 에 해당하는 영수증이 없습니다."}, status=404)
        except Receipt.DoesNotExist:
            return Response({"detail": f"receipt_id={receipt_id} 에 해당하는 영수증이 없습니다."}, status=404)

        # 2) 영수증 측 주소 추출
        # 저장 시 store_address를 이미 넣었다면 그대로 사용
        receipt_store_address = getattr(receipt, "store_address", None)
        if not receipt_store_address:
            # 저장된 원본에서 꺼낼 수도 있음(필요 시)
            raw = getattr(receipt, "receipt_result_raw", {}) or {}
            store_info = (raw.get("storeInfo") or {})
            # formatted 우선, 없으면 text
            receipt_store_address = None
            addrs = store_info.get("addresses") or []
            if addrs:
                first = addrs[0] or {}
                receipt_store_address = (first.get("formatted") or {}).get("value") or first.get("text") or ""
        receipt_store_address = receipt_store_address or ""

        # 3) 현재 상점 주소 조회(도로명/지번)
        try:
            current_store = Store.objects.get(id=store_id)
            roadname_addr = current_store.roadname_address or ""
            number_addr   = current_store.number_address or ""
        except Store.DoesNotExist:
            # DB에 없으면 빈값 비교로 처리
            roadname_addr = ""
            number_addr   = ""

        # 4) 비교
        cmp = compare_address(
            ocr_addr=receipt_store_address,
            roadname_addr=roadname_addr,
            number_addr=number_addr,
        )

        # best_type 기준으로 응답용 주소 선택
        chosen_store_addr = roadname_addr if cmp["best_type"] == "roadname" else number_addr

        # 5) 영수증 메타(상호/날짜/총액)도 같이 반환하면 프론트가 표시하기 좋음
        receipt_store_name = getattr(receipt, "store_name", None)
        receipt_date = getattr(receipt, "payment_date", None)
        receipt_total_price = getattr(receipt, "total_amount", None)

        payload = {
            "receipt": {
                "id": receipt.id,
                "image_uid": getattr(receipt, "image_uid", None),
                "store_name": receipt_store_name,
                "store_address": receipt_store_address,
                "payment_date": receipt_date,
                "total_amount": receipt_total_price,
            },
            "current_store_address": chosen_store_addr,
            "address_match": cmp["match"],
            "best_type": cmp["best_type"],
            "best_scores": cmp["best_scores"],
            "road_scores": cmp["road_scores"],
            "number_scores": cmp["number_scores"],
            "normalized": {
                "receipt": normalize_address(receipt_store_address),
                "roadname": normalize_address(roadname_addr),
                "number": normalize_address(number_addr),
            }
        }
        if cmp["match"]:
            payload["message"] = "주소가 일치하거나 허용 범위 내에서 일치합니다."
            return Response(payload, status=200)
        else:
            payload["message"] = "영수증 주소와 가게 주소가 일치하지 않습니다."
            return Response(payload, status=400)

class StoreView(APIView):
    def post(self, request):
        serializer = StoreSerializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)