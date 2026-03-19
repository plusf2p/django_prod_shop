from django.conf import settings
from django.urls import reverse
from django.db import transaction
from django.db.models import Prefetch

from rest_framework import status
from rest_framework.response import Response

from yookassa import Configuration, Payment as YooPayment

from django_prod_shop.payment.models import Payment
from django_prod_shop.orders.models import Order, OrderItem


def create_payment(request, order_id):
    Configuration.account_id = settings.YOOKASSA_SHOP_ID
    Configuration.secret_key = settings.YOOKASSA_SECRET_KEY

    return_url = request.build_absolute_uri(reverse('payment:payment_completed'))

    with transaction.atomic():
        order = Order.objects.prefetch_related(
            Prefetch('items', queryset=OrderItem.objects.select_related('product'))
        ).get(order_id=order_id)
        
        amount = order.total_price_after_discount

        items = []
        for item in order.items.all():
            quantity = item.quantity
            items.append({
                "description": item.product.title[:100],
                "quantity": str(quantity),
                "amount": {
                    "value": str(item.cost),
                    "currency": "RUB",
                },
                "vat_code": '1',
            })
            item.product.reserved_quantity += quantity
            item.product.save()

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


def confirm_payment(order_id, yk_id):
    with transaction.atomic():
        order = Order.objects.prefetch_related(
            Prefetch('items', queryset=OrderItem.objects.select_related('product'))
        ).prefetch_related('payment').select_for_update().get(order_id=order_id)

        order.status = Order.StatusChoices.PAID
        order.yookassa_id = yk_id
        order.save()

        for item in order.items.all():
            quantity = item.quantity
            item.product.quantity -= quantity
            item.product.reserved_quantity -= quantity
            item.product.save()

        order.payment.status = Payment.StatusChoices.PAID
        order.payment.save()


def cancel_payment(order_id, yk_id):
    with transaction.atomic():
        order = Order.objects.prefetch_related(
            Prefetch('items', queryset=OrderItem.objects.select_related('product'))
        ).prefetch_related('payment').select_for_update().get(order_id=order_id)

        order.status = Order.StatusChoices.CANCELLED
        order.yookassa_id = yk_id
        order.save()

        for item in order.items.all():
            quantity = item.quantity
            item.product.reserved_quantity -= quantity
            item.product.save()

        order.payment.status = Payment.StatusChoices.CANCELLED
        order.payment.save()
