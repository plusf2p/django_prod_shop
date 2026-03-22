from rest_framework.routers import DefaultRouter

from .api.views import CouponViewSet


app_name = 'coupons'

router = DefaultRouter()

router.register('coupons', CouponViewSet, basename='coupons')

urlpatterns = router.urls
