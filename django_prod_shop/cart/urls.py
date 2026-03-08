from rest_framework.routers import DefaultRouter

from .api import views as api_views


app_name = 'cart'

router = DefaultRouter()
router.register('cart', api_views.CartViewSet, basename='cart')

urlpatterns = router.urls
