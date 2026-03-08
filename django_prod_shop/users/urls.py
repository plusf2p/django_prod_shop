from django.urls import path

from rest_framework.routers import DefaultRouter

from rest_framework_simplejwt.views import TokenRefreshView

import django_prod_shop.users.api.views as api_views
from .views import user_detail_view, user_redirect_view, user_update_view


app_name = "users"

router = DefaultRouter()
router.register('profile', api_views.ProfileViewSet)

urlpatterns = [
    path("~redirect/", view=user_redirect_view, name="redirect"),
    path("~update/", view=user_update_view, name="update"),
    path("<int:pk>/", view=user_detail_view, name="detail"),

    path('register/', api_views.RegisterViewSet.as_view({'post': 'create'}), name='register'),
    path('token/', api_views.MyTokenObtainPairView.as_view(), name='token_access'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]

urlpatterns += router.urls
