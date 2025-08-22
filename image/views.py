import boto3
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.conf import settings
import uuid 


class GetPresignedUrlView(APIView):
    def post(self, request, *args, **kwargs):
        original_filename = request.data.get('filename')
        
        if not original_filename:
            return Response({'error': 'filename is required'}, status=status.HTTP_400_BAD_REQUEST)
        
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
        

class SaveProfileImageView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        s3_url = request.data.get('s3_url')

        if not s3_url:
            return Response({'error': 's3_url is required'}, status=status.HTTP_400_BAD_REQUEST)

        user = request.user

        user.profile_image = s3_url
        user.save()

        return Response({
            'message': 'Profile image URL saved successfully.',
            's3_url': s3_url
        }, status=status.HTTP_200_OK)
    
class GetUserProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        # 현재 로그인된 사용자의 객체를 가져옵니다.
        user = request.user

        # 사용자 프로필 정보를 JSON 형식으로 반환합니다.
        # 이 데이터는 필요에 따라 더 많은 필드를 포함할 수 있습니다.
        profile_data = {
            'username': user.username,
            'email': user.email,
            'nickname': user.nickname,
            'profile_image_url': user.profile_image,  # DB에 저장된 S3 URL
        }
