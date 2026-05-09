from yookassa import Configuration, Payment as YooPayment
from decimal import Decimal
from typing import Any

from django.conf import settings

from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.request import Request
from rest_framework.views import APIView
from rest_framework import status

from .services import confirm_payment, cancel_payment
from .models import Payment


class YookassaWebhookAPIView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        data = request.data
        obj = data.get('object', {})

        payment_id = obj.get('id')

        if not payment_id:
            return Response({'error': 'Нет ID платежа'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            payment = Payment.objects.select_related('order').get(payment_id=payment_id)
        except Payment.DoesNotExist:
            return Response({'error': 'Платеж не найден'}, status=status.HTTP_404_NOT_FOUND)

        if payment.order is None:
            return Response({'error': 'У платежа нет заказа'}, status=status.HTTP_400_BAD_REQUEST)

        Configuration.account_id = settings.YOOKASSA_SHOP_ID
        Configuration.secret_key = settings.YOOKASSA_SECRET_KEY

        try:
            yoo_payment = YooPayment.find_one(payment_id)
        except Exception:
            return Response(
                {'error': 'Не удалось проверить платеж в YooKassa'}, 
                status=status.HTTP_400_BAD_REQUEST,
            )

        if str(yoo_payment.metadata.get('order_id')) != str(payment.order.order_id):
            return Response(
                {'error': 'Order ID не совпадает'}, status=status.HTTP_400_BAD_REQUEST,
            )

        if yoo_payment.id != payment.payment_id:
            return Response({'error': 'ID платежа не совпадает'}, status=status.HTTP_400_BAD_REQUEST)

        if Decimal(str(yoo_payment.amount.value)) != payment.amount:
            return Response({'error': 'Сумма платежа не совпадает'}, status=status.HTTP_400_BAD_REQUEST)

        if yoo_payment.amount.currency != 'RUB':
            return Response({'error': 'Валюта платежа не совпадает'}, status=status.HTTP_400_BAD_REQUEST)

        if yoo_payment.status == 'succeeded':
            confirm_payment(order_id=payment.order.order_id, yk_id=payment_id)
        elif yoo_payment.status == 'canceled':
            cancel_payment(order_id=payment.order.order_id, yk_id=payment_id)
        else:
            return Response({'status': 'ignored'}, status=status.HTTP_200_OK)

        return Response({'status': 'ok'}, status=status.HTTP_200_OK)
