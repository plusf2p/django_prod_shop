from django.urls import path

from rest_framework.routers import DefaultRouter

# from rest_framework_simplejwt.views import TokenRefreshView

import django_prod_shop.users.api.views as api_views


app_name = "profile"

router_profile = DefaultRouter()
router_profile.register('profile', api_views.ProfileViewSet, basename='profile')

urlpatterns = [
    # path('users/register/', api_views.RegisterViewSet.as_view({'post': 'create'}), name='register'),
    # path('users/change-password/', api_views.ChangePasswordAPIView.as_view(), name='change_password'),
    # path('users/reset-password/', api_views.PasswordResetAPIView.as_view(), name='reset_password'),
    # path('users/reset-password/confirm/', api_views.PasswordResetConfirmAPIView.as_view(), name='reset_password_confirm'),
    # path('users/token/', api_views.MyTokenObtainPairView.as_view(), name='token_access'),
    # path('users/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    # path('auth/jwt/create/', api_views.MyTokenObtainPairView.as_view(), name='token_access'),
]

urlpatterns += router_profile.urls
