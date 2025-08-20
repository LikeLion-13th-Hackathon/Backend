from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404 
from rest_framework import status, permissions
from django.db import models, transaction, IntegrityError
from .models import Review, ReviewLike, ReviewTag
from .serializers import ReviewTagSerializer, ReviewCreateSerializer, ReviewUpdateSerializer, ReviewSerializer
from rest_framework.permissions import IsAuthenticated
from stores.models import Store
from accounts.models import User

class ReviewLikeToggleView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request, review_id):
        user = request.user
        try:
            # 좋아요 있으면 삭제
            qs = ReviewLike.objects.filter(user=user, review_id=review_id)
            if qs.exists():
                deleted, _ = qs.delete()
                if deleted:
                    Review.objects.filter(id=review_id).update(
                        likes_count=models.F("likes_count") - 1
                    )
                    likes_count = Review.objects.values_list("likes_count", flat=True).get(id=review_id)
                    return Response({
                        "liked": False,
                        "likes_count": likes_count,
                    }, status=status.HTTP_200_OK)
            else:
                # 좋아요 없으면 생성
                review = Review.objects.get(id=review_id)
                ReviewLike.objects.create(user=user, review=review)
                Review.objects.filter(id=review_id).update(
                    likes_count=models.F("likes_count") + 1
                )
                likes_count = Review.objects.values_list("likes_count", flat=True).get(id=review_id)
                return Response({"liked": True, "likes_count": likes_count}, status=status.HTTP_201_CREATED)
        except Review.DoesNotExist:
            return Response({"detail": "review not found"}, status=status.HTTP_404_NOT_FOUND)
        except IntegrityError:
            liked = ReviewLike.objects.filter(user=user, review_id=review_id).exists()
            likes_count = Review.objects.values_list("likes_count", flat=True).get(id=review_id)
            return Response({"liked": liked, "likes_count": likes_count}, status=status.HTTP_200_OK)

class StoreReviewListView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, store_id):
        # 스토어 존재 검증
        if not Store.objects.filter(pk=store_id).exists():
            return Response({"detail": "Store not found"}, status=status.HTTP_404_NOT_FOUND)

        data = request.data.copy()
        data["store"] = store_id

        serializer = ReviewCreateSerializer(data=data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        review = serializer.save()

        # 읽기용 serializer로 응답
        out = ReviewSerializer(review, context={"request": request})
        return Response(out.data, status=status.HTTP_201_CREATED)
    
    def get(self, request, store_id):
        if not Store.objects.filter(pk=store_id).exists():
            return Response({"detail": "Store not found"}, status=status.HTTP_404_NOT_FOUND)
        
        qs = (
            Review.objects.filter(store_id=store_id)
            .select_related("store", "user")
            .prefetch_related("tags", "likes")  # liked 계산 최적화
            .order_by("-created")  # 필요시 created 기준으로 변경
        )

        serializer = ReviewSerializer(qs, many=True, context={"request": request})
        return Response({"results": serializer.data},
            status=status.HTTP_200_OK,)

class UserReviewListView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, user_id):
        # 유저 존재 검증
        if not User.objects.filter(pk=user_id).exists():
            return Response({"detail": "User not found"}, status=status.HTTP_404_NOT_FOUND)
        
        qs = (
            Review.objects.filter(user_id=user_id)
            .select_related("store", "user")
            .prefetch_related("tags", "likes")  # liked 계산 최적화
            .order_by("-created")  # 필요시 created 기준으로 변경
        )

        serializer = ReviewSerializer(qs, many=True, context={"request": request})
        return Response({"results": serializer.data},
            status=status.HTTP_200_OK,)

class ReviewView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, review_id):

        review = get_object_or_404(Review, id=review_id)
        serializer = ReviewSerializer(review)
        return Response({"results": serializer.data},
            status=status.HTTP_200_OK,)
    
    def put(self, request, review_id):
        # 리뷰 로드
        review = (
            Review.objects.select_related("store", "user")
            .prefetch_related("tags", "likes")
            .filter(id=review_id)
            .first()
        )
        if not review:
            return Response({"detail": "Review not found"}, status=status.HTTP_404_NOT_FOUND)

        # 권한 검사: 작성자만 허용
        if review.user_id != request.user.user_id:
            return Response({"detail": "권한이 없습니다."}, status=status.HTTP_403_FORBIDDEN)

        # PUT은 전체 갱신: partial=False
        serializer = ReviewUpdateSerializer(
            review, data=request.data, partial=False, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        review = serializer.save()

        # 읽기용 시리얼라이저로 응답
        out = ReviewSerializer(review, context={"request": request})
        return Response(out.data, status=status.HTTP_200_OK)
    
    def delete(self, request, review_id):
        review = Review.objects.filter(id=review_id).first()
        if not review:
            return Response({"detail": "Review not found"}, status=status.HTTP_404_NOT_FOUND)
        
        if review.user_id != request.user.user_id:
            return Response({"detail": "권한이 없습니다."}, status=status.HTTP_403_FORBIDDEN)

        review.delete()
        return Response({"detail": "리뷰 삭제 성공"}, status=status.HTTP_204_NO_CONTENT)

class TagListView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        category = request.query_params.get("category")
        group = request.query_params.get("group")

        qs = ReviewTag.objects.all()

        if category:
            qs = qs.filter(category=category)
        if group:
            qs = qs.filter(group=group)

        qs = qs.order_by("category", "group", "tag", "id")

        serializer = ReviewTagSerializer(qs, many=True)
        return Response(serializer.data)