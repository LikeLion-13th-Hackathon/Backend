from rest_framework import generics
from .models import Store
from .serializers import StoreSerializer
from django.db.models import Count, Q, Prefetch
from reviews.models import Review

class StoreList(generics.ListAPIView):
    serializer_class = StoreSerializer
    
    def get_queryset(self):
        queryset = Store.objects.annotate(review_count=Count('reviews')).order_by('store_id')

        # Prefetch 객체를 사용하여 각 가게의 좋아요가 가장 많은 리뷰를 미리 get
        most_liked_reviews_prefetch = Prefetch(
            'reviews',
            queryset=Review.objects.order_by('-likes_count'),
            to_attr='most_liked_review_obj'
        )
        queryset = queryset.prefetch_related(most_liked_reviews_prefetch)
        
        market = self.request.query_params.get('market')
        category = self.request.query_params.get('category')
        sort_by = self.request.query_params.get('sort_by')
        search_query = self.request.query_params.get('search_query')

        # 필터링
        if market:
            queryset = queryset.filter(market=market)
        
        if category:
            queryset = queryset.filter(category=category)

        if search_query:
            queryset = queryset.filter(
                Q(store_name__icontains=search_query) | 
                Q(store_english__icontains=search_query) |
                Q(market__market_name__icontains=search_query) | # 시장 한글명
                Q(market__market_english__icontains=search_query) # 시장 영어명
            )
        
        # 정렬 
        if sort_by == 'english':
            return queryset.order_by('store_english')
        elif sort_by == 'reviews':
            return queryset.order_by('-review_count')
        
        return queryset.order_by('store_english') 