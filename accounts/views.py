from django.shortcuts import render, redirect
from rest_framework_simplejwt.serializers import RefreshToken
from rest_framework.views import APIView
from rest_framework.response import Response
from .serializers import *
from rest_framework import status
from django.shortcuts import get_object_or_404 
from rest_framework.permissions import IsAuthenticated #logout
from django.contrib.auth import logout #logout

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
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']

        # 토큰 생성
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        refresh_token = str(refresh)

        res = Response(
            {
                "user": {
                    "id": user.user_id,
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

class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        logout(request)
        return Response({"message": "logout success!"}, status=status.HTTP_200_OK)
    
class UserInfoView(APIView):
    def get(self, request, user_id):

        user = get_object_or_404(User, user_id=user_id)
        serializer = UserSerializer(user)
        return Response({"results": serializer.data},
            status=status.HTTP_200_OK,)