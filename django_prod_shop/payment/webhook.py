from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

from .services import confirm_payment, cancel_payment
from .models import Payment


class YookassaWebhookAPIView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        data = request.data
        obj = data.get("object", {})

        payment_id = obj.get('id')
        status_event = obj.get('status')

        if not payment_id:
            return Response({'error': 'Нет ID платежа'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            payment = Payment.objects.select_related('order').get(payment_id=payment_id)
        except Payment.DoesNotExist:
            return Response({'error': 'Платеж не найден'}, status=status.HTTP_404_NOT_FOUND)

        if payment.order is None:
            return Response({'error': 'У платежа нет заказа'}, status=status.HTTP_400_BAD_REQUEST)

        # try:
        #     if status_event == 'succeeded':
        #         confirm_payment(order_id=payment.order.order_id, yk_id=payment_id)

        #         # if payment.order.release_task_id:
        #         #     current_app.revoke(payment.order.release_task_id, terminate=True)
        #         #     payment.order.release_task_id = None
        #         #     payment.order.save()

        #     elif status_event == 'canceled':
        #         cancel_payment(order_id=payment.order.order_id, yk_id=payment_id)
        #     else:
        #         return Response({'status': 'ignored'}, status=status.HTTP_200_OK)
        # except Exception as e:
        #     return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



        if status_event == 'succeeded':
            confirm_payment(order_id=payment.order.order_id, yk_id=payment_id)
        elif status_event == 'canceled':
            cancel_payment(order_id=payment.order.order_id, yk_id=payment_id)
        else:
            return Response({'status': 'ignored'}, status=status.HTTP_200_OK)



        return Response({'status': 'ok'}, status=status.HTTP_200_OK)
