from rest_framework.routers import DefaultRouter

from django.urls import path

from api import views as api_views
from .webhook import YookassaWebhookAPIView


app_name = 'payment'

router = DefaultRouter()

router.register('paymant', api_views.PaymentViewSet)

urlpattenrs = [
    path('webhook/', YookassaWebhookAPIView.as_view(), name='payment_webhook'),
    path('completed/', api_views.payment_completed, name='payment_completed'),
]

urlpattenrs += router.urls
