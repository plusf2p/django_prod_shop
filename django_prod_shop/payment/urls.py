from rest_framework.routers import DefaultRouter

from django.urls import path

from .api import views as api_views
from .webhook import YookassaWebhookAPIView


app_name = 'payment'

router = DefaultRouter()

router.register('payment', api_views.PaymentViewSet, basename='payment')

urlpatterns = [
    path('webhook/', YookassaWebhookAPIView.as_view(), name='payment-webhook'),
    path('completed/', api_views.payment_completed, name='payment-completed'),
]

urlpatterns += router.urls
