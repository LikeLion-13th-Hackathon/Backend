from django.shortcuts import render, redirect
from rest_framework_simplejwt.serializers import RefreshToken
from rest_framework.views import APIView
from rest_framework.response import Response
from .serializers import *
from rest_framework import status
from django.shortcuts import get_object_or_404 
from rest_framework.permissions import IsAuthenticated #logout
from django.contrib.auth import logout #logout
from django.db.models import Count
from django.db import transaction
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from .models import User, RewardHistory

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
    permission_classes = [IsAuthenticated]
    def get(self, request):
        user_id = request.user.user_id
        user_qs = User.objects.filter(user_id=user_id).annotate(
            visited_count_calc=Count("reviews__store", distinct=True)  # related_name이 review_set이면 "review__store"
        )
        user = get_object_or_404(user_qs)
        serializer = UserSerializer(user)
        return Response({"results": serializer.data},
            status=status.HTTP_200_OK,)
    

def add_reward(user_id: int, delta: int, caption: str = "") -> dict:
    """
    delta: 적립은 양수(+), 차감은 음수(-)
    - 사용자 잔액이 부족한데 차감하려 하면 ValidationError 발생
    """
    if delta == 0:
        raise ValidationError("변경 포인트(delta)는 0이 될 수 없습니다.")

    with transaction.atomic():
        # 행 잠금으로 동시성 제어
        user = User.objects.select_for_update().get(pk=user_id)

        new_balance = (user.reward_count or 0) + delta
        if new_balance < 0:
            raise ValidationError("포인트가 부족합니다.")

        # User 잔액 갱신
        user.reward_count = new_balance
        user.save(update_fields=['reward_count'])

        # 히스토리 생성 (음수 허용)
        rh = RewardHistory.objects.create(
            user=user,
            caption=caption or ("적립" if delta > 0 else "차감"),
            point=delta
        )

        return {
            'balance': new_balance,
            'changed': delta,
            'history_id': rh.id,
        }
    
class RewardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        qs = (
            RewardHistory.objects.filter(user_id=user.user_id)
            .select_related("user")
            .order_by("-created")  # 필요시 created 기준으로 변경
        )
        serializer = RewardHistoryReadSerializer(qs, many=True, context={"request": request})
        return Response(
            {
                "balance": user.reward_count,
                "results": serializer.data
                },
            status=status.HTTP_200_OK,
        )


    def post(self, request):
        serializer = RewardChangeSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        user_id = request.user.user_id  # 본인만 변경
        try:
            result = add_reward(
                user_id=user_id,
                delta=data['delta'],
                caption=data['caption'],
            )
            return Response(
                {
                    "delta": data['delta'],
                    "caption": data['caption'],
                    "balance": result["balance"],
                    "changed": result["changed"],
                    "history_id": result["history_id"],
                },
                status=status.HTTP_200_OK,
            )
        except ObjectDoesNotExist:
            return Response({"detail": "User not found"}, status=status.HTTP_404_NOT_FOUND)
        except ValidationError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    

