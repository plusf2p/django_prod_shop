from django.urls import path

from rest_framework.routers import DefaultRouter

from rest_framework_simplejwt.views import TokenRefreshView

import django_prod_shop.users.api.views as api_views


app_name = "users"

router = DefaultRouter()
router.register('profile', api_views.ProfileViewSet)

urlpatterns = [
    path('users/register/', api_views.RegisterViewSet.as_view({'post': 'create'}), name='register'),
    path('users/token/', api_views.MyTokenObtainPairView.as_view(), name='token_access'),
    path('users/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]

urlpatterns += router.urls
