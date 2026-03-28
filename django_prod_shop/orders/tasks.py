from celery import shared_task
from celery.utils.log import get_task_logger

from django.db.models import Prefetch
from django.core.mail import send_mail
from django.conf import settings

from django_prod_shop.orders.models import Order, OrderItem


logger = get_task_logger(__name__)


@shared_task
def send_order_email(order_id):
    order = Order.objects.select_related('coupon').select_related('user').prefetch_related(
        Prefetch('items', queryset=OrderItem.objects.select_related('product'))
    ).get(order_id=order_id)

    if not order.user or not order.user.email:
        return

    text = [
        f'Заказ #{order.order_id}',
        f'Сумма со скидкой: {order.total_price}₽\n\n',
        'Ваш заказ:',
    ]

    for item in order.items.all():
        text.append(f'{item.product.title} x {item.quantity} | {item.cost}₽')

    order_status = order.get_status_display()
    coupon = order.coupon.code if order.coupon_id else 'Нет'

    text.extend([
        f'\nСкидка: {order.discount_price or 0}₽. Купон: {coupon}.',
        f'Статус заказа: {order_status}.\n',
        'Детали заказа:',
        f'Имя: {order.full_name}',
        f'Телефон: {order.phone}',
        f'Адрес: {order.address}',
        f'Город: {order.city}\n',
        'Спасибо за заказ!',
    ])

    # logger.info('\n'.join(text))

    send_mail(
        subject=f'Заказ из магазина "{settings.SHOP_NAME}"',
        message='\n'.join(text),
        from_email=settings.EMAIL_HOST_USER,
        recipient_list=[order.user.email],
        fail_silently=False,
    )
