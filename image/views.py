import boto3
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
import uuid 

class GetPresignedUrlView(APIView):
    def post(self, request, *args, **kwargs):
        # 1. 클라이언트로부터 파일 이름 받기 (옵션)
        # 클라이언트가 제공한 파일 이름 대신 서버에서 고유한 이름을 생성하는 것이 좋습니다.
        original_filename = request.data.get('filename')
        
        if not original_filename:
            return Response({'error': 'filename is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        # 2. 고유한 파일 이름 생성
        file_extension = original_filename.split('.')[-1]
        unique_filename = f"{uuid.uuid4()}.{file_extension}"
        
        s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION
        )
        
        try:
            # 3. 프리사인드 URL 생성
            presigned_url = s3_client.generate_presigned_url(
                ClientMethod='put_object',  # 파일 업로드를 위한 'PUT' 메서드
                Params={
                    'Bucket': settings.AWS_STORAGE_BUCKET_NAME,
                    'Key': unique_filename,
                    'ContentType': 'image/jpeg' # 업로드할 파일의 Content-Type
                },
                ExpiresIn=3600  # URL 유효 시간 (초 단위, 1시간)
            )
            
            # 4. 생성된 URL과 S3 주소 반환
            s3_url = f"https://{settings.AWS_STORAGE_BUCKET_NAME}.s3.{settings.AWS_REGION}.amazonaws.com/{unique_filename}"
            
            return Response({
                'presigned_url': presigned_url,
                's3_url': s3_url
            })
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)