from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response

from django.db import transaction

from .models import Payment


class YookassaWebhookAPIView(APIView):
    def post(self, request):
        data = request.data
        obj = data.get("object", {})

        payment_id = obj.get("id")
        status_event = obj.get("status")

        if not payment_id:
            return Response({"error": "Нет ID платежа"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            payment = Payment.objects.get(payment_id=payment_id)
        except Payment.DoesNotExist:
            return Response({"error": "Платеж не найден"}, status=status.HTTP_404_NOT_FOUND)

        # Добавить транзакции
        try:
            with transaction.atomic():
                if status_event == "succeeded":
                    payment.status = "succeeded"
                    OrderObject.mark_order_as_paid(order_id=payment.order.id)
                    OrderObject.set_order_yookassa_id(order_id=payment.order.id, yk_id=payment_id)

                    if payment.order.release_task_id:
                        current_app.revoke(payment.order.release_task_id, terminate=True)
                        payment.order.release_task_id = None
                        payment.order.save()

                elif status_event == "canceled":
                    payment.status = "canceled"
                    OrderObject.cancel_order(order_id=payment.order.id)
                    OrderObject.set_order_yookassa_id(order_id=payment.order.id, yk_id=payment_id)
                payment.save()
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response({"status": "ok"}, status=status.HTTP_200_OK)
