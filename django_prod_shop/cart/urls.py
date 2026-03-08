from rest_framework.routers import DefaultRouter

from .api import views as api_views


app_name = 'cart'

router = DefaultRouter()
router.register('cart', api_views.CartViewSet)

urlpatterns = router.urls
