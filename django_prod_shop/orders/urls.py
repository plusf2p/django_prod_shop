from django.urls import path

from rest_framework.routers import DefaultRouter

from .api import views as api_views


app_name = 'orders'

router = DefaultRouter()

router.register('orders', api_views.OrderViewSet, basename='orders')

urlpatterns = [
    path('<uuid:order_id>/change-status/', api_views.change_order_status_view, name='change-order-status')
]

urlpatterns += router.urls
