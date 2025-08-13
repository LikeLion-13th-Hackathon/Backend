from django.shortcuts import render, redirect
from rest_framework_simplejwt.serializers import RefreshToken
from rest_framework.views import APIView
from rest_framework.response import Response
from .serializers import *
from rest_framework import status

from rest_framework.permissions import IsAuthenticated #logout
from django.contrib.auth import logout #logout

### google-login ###
from config.settings import get_secret
from urllib.parse import quote

GOOGLE_REDIRECT = get_secret("GOOGLE_REDIRECT")
GOOGLE_CALLBACK_URI = get_secret("GOOGLE_CALLBACK_URI")
GOOGLE_CLIENT_ID = get_secret("GOOGLE_CLIENT_ID")
GOOGLE_SECRET = get_secret("GOOGLE_SECRET")
GOOGLE_SCOPE = get_secret("GOOGLE_SCOPE")

from json import JSONDecodeError
from django.http import JsonResponse
import requests 

class RegisterView(APIView):
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)

        # 유효성 검사 
        if serializer.is_valid(raise_exception=True):
            
            # 유효성 검사 통과 후 객체 생성
            user = serializer.save()

            # user에게 refresh token 발급
            token = RefreshToken.for_user(user)
            refresh_token = str(token)
            access_token = str(token.access_token)

            res = Response(
                {
                    "user": serializer.data,
                    "message": "register success!",
                    "token": {
                        "access_token": access_token,
                        "refresh_token": refresh_token,
                    }, 
                },
                status=status.HTTP_201_CREATED,
            )
            return res

class AuthView(APIView):
    def post(self, request):
        serializer = AuthSerializer(data=request.data)
        
        # 유효성 검사
        if serializer.is_valid(raise_exception=True):
            user = serializer.validated_data['user']
            access_token = serializer.validated_data['access_token']
            refresh_token = serializer.validated_data['refresh_token']

            res = Response(
                {
                    "user": {
                        "id": user.id,
                        "username": user.username,
                        "email": user.email,
                    },
                    "message": "login success!",
                    "token": {
                        "access_token": access_token,
                        "refresh_token": refresh_token,
                    }, 
                },
                status=status.HTTP_200_OK,
            )

            res.set_cookie("access_token", access_token, httponly=True)
            res.set_cookie("refresh_token", refresh_token, httponly=True)
            return res
        
        # 유효성 검사 실패 시 오류 반환
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        logout(request)
        return Response({"message": "logout success!"}, status=status.HTTP_200_OK)
    
### google-login & callback ###
def google_login(request):
    scope = quote(GOOGLE_SCOPE)
    return redirect(f"{GOOGLE_REDIRECT}?client_id={GOOGLE_CLIENT_ID}&response_type=code&redirect_uri={GOOGLE_CALLBACK_URI}&scope={scope}")

def google_callback(request):
    code = request.GET.get("code", None) # 인가코드 받아오기
    
    if code is None:
        return JsonResponse({'error': 'Authorization code error.'}, status=status.HTTP_400_BAD_REQUEST)

    # 인가코드로 access token 받기
    token_req = requests.post(
    "https://oauth2.googleapis.com/token",
    data={
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_SECRET,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": GOOGLE_CALLBACK_URI,
    })

    token_req_json = token_req.json()
    error = token_req_json.get("error")

    if error is not None:
        raise JSONDecodeError(error)

    google_access_token = token_req_json.get('access_token')

    # access token으로 구글 계정 정보 가져오기
    # user_info = requests.get(f"https://www.googleapis.com/oauth2/v3/userinfo?access_token={google_access_token}")
    user_info = requests.get(
    "https://www.googleapis.com/oauth2/v3/userinfo",
    headers={"Authorization": f"Bearer {google_access_token}"})
    res_status = user_info.status_code

    if res_status != 200:
        return JsonResponse({'status': 400,'message': 'Failed to get access token'}, status=status.HTTP_400_BAD_REQUEST)
    
    user_info_json = user_info.json()

    data = {
        "username": user_info_json['name'],
        "email": user_info_json['email']
    }
    
    serializer = OAuthSerializer(data=data)
    if serializer.is_valid(raise_exception=True):
        user = serializer.validated_data["user"]
        access_token = serializer.validated_data["access_token"]
        refresh_token = serializer.validated_data["refresh_token"]

        res = JsonResponse(
            {
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                },
                "message": "google social login success!",
                "token": {
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                },
            },
            status=status.HTTP_200_OK,
        )
        res.set_cookie("access_token", access_token, httponly=True)
        res.set_cookie("refresh_token", refresh_token, httponly=True)
        return res