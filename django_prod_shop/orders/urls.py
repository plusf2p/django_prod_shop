from rest_framework.routers import DefaultRouter

from .api import views as api_views


app_name = 'orders'

router = DefaultRouter()

router.register('order', api_views.OrderViewSet)

urlpatterns = router.urls
