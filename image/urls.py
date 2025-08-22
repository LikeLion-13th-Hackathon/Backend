from django.urls import path
from .views import GetPresignedUrlView, SaveProfileImageView, GetUserProfileView

urlpatterns = [
    path('', GetPresignedUrlView.as_view(), name='get-presigned-url'),
    path('save/', SaveProfileImageView.as_view(), name='save-profile-image'),
    path('profile/', GetUserProfileView.as_view(), name='get-user-profile'),
]