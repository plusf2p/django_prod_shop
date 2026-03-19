from django.db import models

from orders.models import Order


class Payment(models.Model):
    class StatusChoices(models.TextChoices):
        PENDING = 'pending', 'В процессе'
        PAID = 'paid', 'Оплачено'
        CANCELLED = 'cancelled', 'Отменено'

    order = models.OneToOneField(
        Order, null=True, on_delete=models.SET_NULL, related_name='payment', verbose_name='Заказ'
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Количество')
    payment_id = models.CharField(max_length=255, unique=True, db_index=True, verbose_name='ID Платежа')
    status = models.CharField(max_length=20, choices=StatusChoices, default=StatusChoices.PENDING, verbose_name='Статус')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')

    class Meta:
        verbose_name = 'Платеж'
        verbose_name_plural = 'Платежи'
        constaints = [
            models.UniqueConstraint(fields=['order', 'payment_id'], name="unique_order_payment")
        ]

    def __str__(self):
        return f'Заказ ({self.order.order_id}) - {self.status}'
