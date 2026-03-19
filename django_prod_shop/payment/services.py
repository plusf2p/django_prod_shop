from django.conf import settings
from django.urls import reverse
from django.db import transaction, IntegrityError
from django.db.models import Prefetch, F

from rest_framework import status
from rest_framework.response import Response

from yookassa import Configuration, Payment as YooPayment

from django_prod_shop.products.models import Product
from django_prod_shop.orders.models import Order, OrderItem
from django_prod_shop.payment.models import Payment

def create_payment_service(request, order_id):
    Configuration.account_id = settings.YOOKASSA_SHOP_ID
    Configuration.secret_key = settings.YOOKASSA_SECRET_KEY

    email = request.user.email
    if not email:
        return Response(
            {'error': 'У вас не указан email'}, status=status.HTTP_400_BAD_REQUEST,
        )

    return_url = request.build_absolute_uri(reverse('payment:payment_completed'))

    try:
        order = Order.objects.prefetch_related(
            Prefetch('items', queryset=OrderItem.objects.select_related('product'))
        ).get(order_id=order_id)
    except Order.DoesNotExist:
        return Response({'error': 'Такого заказа не существует'}, status=status.HTTP_404_NOT_FOUND)
    
    if (not order.user == request.user) and not request.user.is_staff:
        return Response({'error': 'Вы не можете оплачивать чужой заказ'}, status=status.HTTP_403_FORBIDDEN)

    if Payment.objects.filter(order=order).exists():
        return Response({'error': 'У этого заказа уже есть платеж'}, status=status.HTTP_400_BAD_REQUEST)

    if order.status in [Order.StatusChoices.PAID, Order.StatusChoices.DELIVERED, Order.StatusChoices.CANCELLED]:
        return Response({'error': 'Оплата для этого заказа недоступна'}, status=status.HTTP_400_BAD_REQUEST)

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

    try:
        yoo_payment = YooPayment.create({
            'amount': {'value': str(amount), 'currency': 'RUB'},
            'confirmation': {'type': 'redirect', 'return_url': return_url},
            'capture': True,
            'receipt': {
                'customer': {
                    'email': email
                },
                'items': items,
            },
            'description': f'Заказ #{order_id}',
        })
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    try:
        with transaction.atomic():
            for item in order.items.all():
                Product.objects.filter(pk=item.product_id).update(
                    reserved_quantity=F('reserved_quantity') + item.quantity
                )
            payment = Payment.objects.create(
                order=order,
                amount=amount,
                payment_id=yoo_payment.id,
                status=Payment.StatusChoices.PENDING,
            )
    except IntegrityError as e:
        return Response({'error': 'Не удалось создать платёж. Попробуйте ещё раз'}, status=status.HTTP_400_BAD_REQUEST)
    return Response({
        'id': payment.pk,
        'payment_id': payment.payment_id,
        'confirmation_url': yoo_payment.confirmation.confirmation_url,
    }, status=status.HTTP_201_CREATED)


def confirm_payment(order_id, yk_id):
    with transaction.atomic():
        order = Order.objects.select_for_update().prefetch_related(
            Prefetch('items', queryset=OrderItem.objects.select_related('product'))
        ).select_related('payment').get(order_id=order_id)

        payment = getattr(order, 'payment', None)
        if payment is None:
            return

        if payment.status in [Payment.StatusChoices.PAID, Payment.StatusChoices.CANCELLED]:
            return

        order.status = Order.StatusChoices.PAID
        order.yookassa_id = yk_id
        order.save(update_fields=['status', 'yookassa_id'])

        for item in order.items.all():
            quantity = item.quantity
            Product.objects.filter(pk=item.product_id).update(
                quantity=F('quantity') - quantity,
                reserved_quantity=F('reserved_quantity') - quantity,
            )

        payment.status = Payment.StatusChoices.PAID
        payment.save(update_fields=['status'])


def cancel_payment(order_id, yk_id):
    with transaction.atomic():
        order = Order.objects.select_for_update().prefetch_related(
            Prefetch('items', queryset=OrderItem.objects.select_related('product'))
        ).select_related('payment').get(order_id=order_id)

        payment = getattr(order, 'payment', None)
        if payment is None:
            return

        if payment.status in [Payment.StatusChoices.PAID, Payment.StatusChoices.CANCELLED]:
            return

        order.status = Order.StatusChoices.CANCELLED
        order.yookassa_id = yk_id
        order.save(update_fields=['status', 'yookassa_id'])

        for item in order.items.all():
            Product.objects.filter(pk=item.product_id).update(
                reserved_quantity=F('reserved_quantity') - item.quantity
            )

        payment.status = Payment.StatusChoices.CANCELLED
        payment.save(update_fields=['status'])
