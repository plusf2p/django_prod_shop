from django.conf import settings
from django.urls import reverse
from django.db import transaction
from django.shortcuts import get_object_or_404

from rest_framework import status
from rest_framework.response import Response

from yookassa import Configuration, Payment as YooPayment

from django_prod_shop.payment.models import Payment
from django_prod_shop.orders.models import Order


def create_payment(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    Configuration.account_id = settings.YOOKASSA_SHOP_ID
    Configuration.secret_key = settings.YOOKASSA_SECRET_KEY

    amount = order.total_price_after_discount
    return_url = request.build_absolute_uri(reverse('payment:payment_completed'))

    items = []
    for item in order.items.all():
        items.append({
            "description": item.product.title[:100],
            "quantity": str(item.quantity),
            "amount": {
                "value": str(item.cost),
                "currency": "RUB",
            },
            "vat_code": '1',
        })

    email = request.user.email
    try:
        yoo_payment = YooPayment.create({
            "amount": {"value": str(amount), "currency": "RUB"},
            "confirmation": {"type": "redirect", "return_url": return_url},
            "capture": True,
            "receipt": {
                "customer": {
                    "email": email
                },
                "items": items,
            },
            "description": f"Заказ #{order_id}",
        })
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    with transaction.atomic():
        payment = Payment.objects.create(
            order=order,
            amount=amount,
            payment_id=yoo_payment.id,
            status=Payment.StatusChoices.PENDING,
        )

    return Response({
        "payment_id": payment.pk,
        "confirmation_url": yoo_payment.confirmation.confirmation_url,
    }, status=status.HTTP_200_OK)
