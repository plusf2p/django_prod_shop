from rest_framework.routers import DefaultRouter

from .api.views import ReviewViewSet


app_name = 'reviews'

router = DefaultRouter()

router.register('reviews', ReviewViewSet, basename='reviews')

urlpatterns = router.urls
