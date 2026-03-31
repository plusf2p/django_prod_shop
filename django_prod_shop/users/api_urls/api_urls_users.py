from django.urls import path

from rest_framework_simplejwt.views import TokenRefreshView, TokenVerifyView

import django_prod_shop.users.api.views as api_views


app_name = "users"

urlpatterns = [
    path(
        'users/',
        api_views.MyUserViewSet.as_view({'post': 'create'}),
        name='register',
    ),
    path(
        'users/activation/',
        api_views.MyUserViewSet.as_view({'post': 'activation'}),
        name='user-activation',
    ),
    path(
        'users/resend-activation/',
        api_views.MyUserViewSet.as_view({'post': 'resend_activation'}),
        name='user-resend-activation',
    ),
    path(
        'users/set-password/',
        api_views.MyUserViewSet.as_view({'post': 'set_password'}),
        name='user-set-password',
    ),
    path(
        'users/reset-password/',
        api_views.MyUserViewSet.as_view({'post': 'reset_password'}),
        name='user-reset-password',
    ),
    path(
        'users/reset-password-confirm/',
        api_views.MyUserViewSet.as_view({'post': 'reset_password_confirm'}),
        name='user-reset-password-confirm',
    ),

    path('jwt/create/', api_views.MyTokenObtainPairView.as_view(), name='token-access'),
    path('jwt/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('jwt/verify/', TokenVerifyView.as_view(), name='token-verify'),
]
