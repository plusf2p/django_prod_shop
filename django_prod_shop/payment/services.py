from yookassa import Configuration, Payment as YooPayment
from uuid import UUID

from django.db import transaction, IntegrityError
from django.conf import settings
from django.urls import reverse
from django.db.models import F

from rest_framework.response import Response
from rest_framework.request import Request
from rest_framework import status

from django_prod_shop.products.models import Product
from django_prod_shop.orders.models import Order, StatusChoices as OrderStatusChoices
from django_prod_shop.payment.models import Payment, StatusChoices as PaymentStatusChoices


def create_payment_service(request: Request, order_id: str) -> Response:
    Configuration.account_id = settings.YOOKASSA_SHOP_ID
    Configuration.secret_key = settings.YOOKASSA_SECRET_KEY

    email = request.user.email
    if not email:
        return Response(
            {'email': 'У вас не указан email'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    return_url = request.build_absolute_uri(reverse('payment:payment-completed'))

    try:
        with transaction.atomic():
            order = Order.objects.select_for_update().get(order_id=order_id)

            if order.user != request.user and not request.user.is_staff:
                return Response(
                    {'error': 'Вы не можете оплачивать чужой заказ'},
                    status=status.HTTP_403_FORBIDDEN,
                )

            if Payment.objects.filter(order=order).exists():
                return Response(
                    {'error': 'У этого заказа уже есть платеж'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if order.status in [
                OrderStatusChoices.PAID,
                OrderStatusChoices.DELIVERED,
                OrderStatusChoices.CANCELLED,
            ]:
                return Response(
                    {'error': 'Оплата для этого заказа недоступна'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            amount = order.total_price_after_discount

            items: list[dict[str, object]] = []
            order_items = list(order.items.select_related('product').all())

            for item in order_items:
                items.append({
                    'description': item.product.title[:100],
                    'quantity': str(item.quantity),
                    'amount': {
                        'value': str(item.cost),
                        'currency': 'RUB',
                    },
                    'vat_code': '1',
                })

            for item in order_items:
                product = Product.objects.select_for_update().get(pk=item.product_id)

                available_quantity = product.quantity - product.reserved_quantity

                if item.quantity > available_quantity:
                    return Response(
                        {'error': 'Недостаточно товара на складе'},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                product.reserved_quantity += item.quantity
                product.save(update_fields=['reserved_quantity'])

            try:
                yoo_payment = YooPayment.create({
                    'amount': {'value': str(amount), 'currency': 'RUB'},
                    'confirmation': {'type': 'redirect', 'return_url': return_url},
                    'capture': True,
                    'receipt': {
                        'customer': {'email': email},
                        'items': items,
                    },
                    'metadata': {
                        'order_id': str(order.order_id),
                    },
                    'description': f'Заказ #{order_id}',
                })
            except Exception as e:
                transaction.set_rollback(True)
                return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

            payment = Payment.objects.create(
                order=order,
                amount=amount,
                payment_id=yoo_payment.id,
                status=PaymentStatusChoices.PENDING,
            )

    except Order.DoesNotExist:
        return Response({'error': 'Такого заказа не существует'}, status=status.HTTP_404_NOT_FOUND)
    except IntegrityError:
        return Response(
            {'error': 'Не удалось создать платёж. Попробуйте ещё раз'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    return Response({
        'id': payment.pk,
        'payment_id': payment.payment_id,
        'confirmation_url': yoo_payment.confirmation.confirmation_url,
    }, status=status.HTTP_201_CREATED)


def confirm_payment(order_id: UUID, yk_id: str) -> None:
    with transaction.atomic():
        order = Order.objects.select_for_update().get(order_id=order_id)

        payment = Payment.objects.select_for_update().filter(
            order=order, payment_id=yk_id,
        ).first()

        if payment is None:
            return

        if payment.status in [PaymentStatusChoices.PAID, PaymentStatusChoices.CANCELLED]:
            return

        order.status = OrderStatusChoices.PAID
        order.yookassa_id = yk_id
        order.save(update_fields=['status', 'yookassa_id'])

        for item in order.items.all():
            Product.objects.filter(pk=item.product_id).update(
                quantity=F('quantity') - item.quantity,
                reserved_quantity=F('reserved_quantity') - item.quantity,
            )

        payment.status = PaymentStatusChoices.PAID
        payment.save(update_fields=['status'])


def cancel_payment(order_id: UUID, yk_id: str) -> None:
    with transaction.atomic():
        order = Order.objects.select_for_update().get(order_id=order_id)

        payment = Payment.objects.select_for_update().filter(
            order=order, payment_id=yk_id,
        ).first()

        if payment is None:
            return

        if payment.status in [PaymentStatusChoices.PAID, PaymentStatusChoices.CANCELLED]:
            return

        order.status = OrderStatusChoices.CANCELLED
        order.yookassa_id = yk_id
        order.save(update_fields=['status', 'yookassa_id'])

        for item in order.items.select_related('product').all():
            product = Product.objects.select_for_update().get(pk=item.product_id)
            product.reserved_quantity = max(product.reserved_quantity - item.quantity, 0)
            product.save(update_fields=['reserved_quantity'])

        payment.status = PaymentStatusChoices.CANCELLED
        payment.save(update_fields=['status'])
