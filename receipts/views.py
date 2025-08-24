from django.shortcuts import render
from django.http import JsonResponse 
from django.shortcuts import get_object_or_404 
from django.views.decorators.http import require_http_methods
from stores.models import Store 
from .models import * 
from rest_framework.views import APIView   
from rest_framework.response import Response
from rest_framework import status
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
import re
from rest_framework.permissions import IsAuthenticated
from io import BytesIO
from PIL import Image, ImageOps
import imghdr

MAX_OCR_BYTES = 1_000_000  # 1MB

class GetReceiptPresignedUrlView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        original_filename = request.data.get("filename")
        prefix = "receipt/"

        if not original_filename:
            return Response({"error": "filename is required"}, status=status.HTTP_400_BAD_REQUEST)

        # jpg로 강제
        unique_filename = f"{uuid.uuid4()}.jpg"
        key = f"{prefix}{unique_filename}"

        s3_client = boto3.client(
            "s3",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION,
        )

        content_type = "image/jpeg"

        try:
            presigned_url = s3_client.generate_presigned_url(
                ClientMethod="put_object",
                Params={
                    "Bucket": settings.AWS_STORAGE_BUCKET_NAME,
                    "Key": key,
                    "ContentType": content_type,
                },
                ExpiresIn=3600,
            )

            s3_url = f"https://{settings.AWS_STORAGE_BUCKET_NAME}.s3.{settings.AWS_REGION}.amazonaws.com/{key}"

            return Response({
                "presigned_url": presigned_url,
                "s3_url": s3_url,
                "key": key,
                "content_type": content_type,
                "expires_in": 3600,
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

def upload_receipt_to_s3(data: bytes, filename: str | None = None) -> str:
    s3_client = boto3.client(
        "s3",
        aws_access_key_id=getattr(settings, "AWS_ACCESS_KEY_ID", None),
        aws_secret_access_key=getattr(settings, "AWS_SECRET_ACCESS_KEY", None),
        region_name=getattr(settings, "AWS_REGION", None),
    )
    bucket = settings.AWS_STORAGE_BUCKET_NAME
    region = settings.AWS_REGION

    if not filename:
        filename = f"{uuid.uuid4()}.jpg"
    key = f"receipt/{filename}"

    s3_client.put_object(
        Bucket=bucket,
        Key=key,
        Body=data,
        ContentType="image/jpeg",
    )

    return f"https://{bucket}.s3.{region}.amazonaws.com/{key}"

def to_jpeg_under_1mb(django_file) -> tuple[bytes, str]:
    # 1MB 넘는 파일 다운그레이드, jpeg 변환
    raw = django_file.read()
    django_file.seek(0)

    try:
        with Image.open(BytesIO(raw)) as im:
            im = ImageOps.exif_transpose(im)
            if im.mode in ("RGBA", "LA", "P"):
                im = im.convert("RGB")
            elif im.mode != "RGB":
                im = im.convert("RGB")

            # 원본 해상도에서 품질 조정
            jpeg_bytes = _encode_jpeg_under_limit(im, target_bytes=MAX_OCR_BYTES)
            if jpeg_bytes is not None:
                # 파일명 교체
                base_name = getattr(django_file, "name", "upload")
                if "." in base_name:
                    base_name = base_name.rsplit(".", 1)[0]
                return jpeg_bytes, f"{base_name}.jpg"

            # 줄어들 때까지 다운그레이드
            w, h = im.size
            for scale in (0.9, 0.8, 0.7, 0.6, 0.5):
                nw, nh = int(w * scale), int(h * scale)
                if nw < 64 or nh < 64:
                    break
                im_resized = im.resize((nw, nh), Image.LANCZOS)
                jpeg_bytes = _encode_jpeg_under_limit(im_resized, target_bytes=MAX_OCR_BYTES)
                if jpeg_bytes is not None:
                    base_name = getattr(django_file, "name", "upload")
                    if "." in base_name:
                        base_name = base_name.rsplit(".", 1)[0]
                    return jpeg_bytes, f"{base_name}.jpg"

    except Exception as e:
        raise ValueError(f"이미지 변환 실패: {e}")

    raise ValueError("1MB 이하 JPEG로 변환 실패")

def _encode_jpeg_under_limit(im: Image.Image, target_bytes=MAX_OCR_BYTES):
    
    # JPEG 인코딩
    for q in (85, 80, 75, 70, 60, 50):
        buf = BytesIO()
        try:
            im.save(buf, format="JPEG", quality=q, optimize=True, progressive=True)
        except OSError:
            # optimize 실패 시 재시도
            buf = BytesIO()
            im.save(buf, format="JPEG", quality=q)
        data = buf.getvalue()
        if len(data) <= target_bytes:
            return data
    return None

logger = logging.getLogger(__name__)

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
    permission_classes = [IsAuthenticated]
    def post(self, request):
        # 이미지 파일 받기
        image_file = request.FILES.get("file")
        if not image_file:
            return Response({"detail": "file 필드로 이미지를 업로드하세요."}, status=400)

        # 파일 JPEG <= 1MB로 강제 변환
        try:
            jpeg_bytes, new_name = to_jpeg_under_1mb(image_file)
        except ValueError as e:
            return Response({"detail": str(e)}, status=400)
        
        # 네이버 OCR 호출

        OCR_URL = "https://e140deli82.apigw.ntruss.com/custom/v1/45208/063b748a49735894d8ed5ccb7d319025d142b0ce3854fafec62ee3053ba2da0d/document/receipt"

        message = {
            "version": "V2",
            "requestId": str(uuid.uuid4()),
            "timestamp": int(timezone.now().timestamp() * 1000),
            "images": [{"format": "jpg", "name": new_name}],
        }
        files = {
            "file": (new_name, BytesIO(jpeg_bytes), "image/jpeg"),
            "message": (None, json.dumps(message), "application/json"),
        }
        headers = {"X-OCR-SECRET": settings.X_OCR_SECRET}

        try:
            res = requests.post(OCR_URL, headers=headers, files=files, timeout=30)
            res.raise_for_status()
            ocr = res.json()
        except Exception as e:
            return Response({"detail": f"OCR 호출 실패: {e}"}, status=502)

        # OCR 응답에서 images[].receipt만 저장
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
                store_address=store_address,
                total_amount=total_amount,
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

        try:
            s3_url = upload_receipt_to_s3(jpeg_bytes, filename=new_name)  # receipt/{new_name}
        except Exception as e:
            # S3 업로드 실패를 치명적으로 볼지 선택. 일반적으로 여기서 502를 반환.
            return Response({"detail": f"S3 업로드 실패: {e}"}, status=502)

        saved.append({
        "id": row.id,
        "store_name": row.store_name,
        "store_address": row.store_address,
        "payment_datetime": row.payment_datetime,
        "total_amount": row.total_amount,
        })
        resp_saved = ReceiptSerializer(saved, many=True).data
        return Response({"saved": resp_saved, "skipped": skipped}, status=status.HTTP_201_CREATED if saved else status.HTTP_200_OK)
    
def normalize_address(addr: str) -> str:
    if not addr:
        return ""
    s = str(addr).strip()

    # 문자열 전체가 괄호로 시작·끝하면 한 겹 벗기기((), [], {})
    # ex) "(서울 중구 ...)" -> "서울 중구 ..."
    pairs = [("(", ")"), ("[", "]"), ("{", "}")]
    changed = True
    while changed and s:
        changed = False
        for left, right in pairs:
            if len(s) >= 2 and s[0] == left and s[-1] == right:
                s = s[1:-1].strip()
                changed = True
    # 다중 공백 -> 하나
    s = " ".join(s.split())
    # 쉼표/마침표만 제거(하이픈은 유지)
    for ch in [",", "."]:
        s = s.replace(ch, " ")
    # 3) 괄호 안의 내용 제거
    s = re.sub(r"\([^)]*\)", " ", s)  # ()
    s = re.sub(r"\[[^\]]*\]", " ", s) # []
    s = re.sub(r"\{[^}]*\}", " ", s)  # {}
    # 특별시 변환
    for token in ("서울특별시", "서울시"):
        s = s.replace(token, "서울")
    s = " ".join(s.split())
    return s

def score_pair(a: str, b: str) -> dict:
    na, nb = normalize_address(a), normalize_address(b)
    return {
        "ratio": fuzz.ratio(na, nb),
        "partial": fuzz.partial_ratio(na, nb),
        "a": na,  # 디버깅용
        "b": nb,  # 디버깅용
    }

def best_of_store(ocr_addr: str, store) -> dict:
    # 도로명/지번 각각 채점 후 더 좋은 쪽을 점포의 대표 점수로 채택
    road = getattr(store, "road_address", "") or ""
    street = getattr(store, "street_address", "") or ""

    road_s = score_pair(ocr_addr, road)
    num_s  = score_pair(ocr_addr, street)

    road_score = max(road_s["ratio"], road_s["partial"])
    num_score = max(num_s["ratio"], num_s["partial"])

    if (road_score > num_score) or (road_score == num_score and road_s["partial"] >= num_s["partial"]):

        chosen_type = "roadname"
        chosen_score = road_score
    else:
        chosen_type = "number"
        chosen_score = num_score

    return {
        "store_id": getattr(store, "store_id", getattr(store, "id", None)),
        "store_name": getattr(store, "store_name", None),
        "store_image": getattr(store, "store_image", None),
        "select_type": chosen_type,           # 'roadname' | 'number'
        "score": chosen_score,
        # "road_scores": road_s,
        # "number_scores": num_s,
        "road_address": getattr(store, "road_address", None),
        "street_address": getattr(store, "street_address", None),
        # "normalized": {
        #     "road": normalize_address(getattr(store, "road_address", "") or ""),
        #     "street": normalize_address(getattr(store, "street_address", "") or ""),
        # },
        "id": getattr(store, "id", getattr(store, "store_id", 0)), # 보조 정렬용
    }

class ReceiptAddressCompareView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        receipt_id = self.request.query_params.get('receipt_id')
        if not receipt_id:
            return Response({"detail": "receipt_id는 필수입니다."}, status=400)
       
        # 영수증 조회 
        try:
            receipt = Receipt.objects.get(id=receipt_id)
        except Receipt.DoesNotExist:
            return Response({"detail": f"receipt_id={receipt_id} 에 해당하는 영수증이 없습니다."}, status=404)

        # 영수증의 주소 추출
        receipt_store_address = getattr(receipt, "store_address", None)

        # 정규화
        norm_receipt_addr = normalize_address(receipt_store_address)
        if not norm_receipt_addr:
            return Response(
                {
                    "detail": "영수증에서 주소를 추출/정규화하지 못했습니다.",
                    "receipt_address": receipt_store_address,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        scored = []
        for s in Store.objects.all():
            scored.append(best_of_store(norm_receipt_addr, s))

        scored.sort(key=lambda x: (-x["score"], x["id"]))

        return Response(
                {
                    "receipt": {
                        "id": receipt.id,
                        "store_name": getattr(receipt, "store_name", None),
                        "store_address": receipt_store_address,
                        "payment_date": getattr(receipt, "payment_date", None),
                    },
                    "normalized": {
                        "receipt": norm_receipt_addr,
                    },
                    "candidates": scored[:5],  # 점수 높은 순 전체
                    "message": "점수 높은 순 5개",
                },
                status=status.HTTP_200_OK
            )