from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.db import models, transaction, IntegrityError
from .models import Review, ReviewLike, ReviewTag
from .serializers import ReviewTagSerializer

class ReviewLikeToggleView(APIView):
    permission_classes = [permissions.IsAuthenticated]

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

class ReviewView(APIView):
    def post(self, request):
        user = request.user

class TagListView(APIView):
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