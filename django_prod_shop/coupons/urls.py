from rest_framework.routers import DefaultRouter

from .api.views import CouponsViewSet


app_name = 'coupons'

router = DefaultRouter()

router.register('coupons', CouponsViewSet, basename='coupons')

urlpatterns = router.urls
