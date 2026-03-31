from django.urls import path

from rest_framework.routers import DefaultRouter

import django_prod_shop.users.api.views as api_views


app_name = "profile"

router_profile = DefaultRouter()
router_profile.register('profile', api_views.ProfileViewSet, basename='profile')

urlpatterns = router_profile.urls
