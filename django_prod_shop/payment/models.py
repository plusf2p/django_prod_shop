from django.db import models

from django_prod_shop.orders.models import Order


class StatusChoices(models.TextChoices):
    PENDING = 'pending', 'В процессе'
    PAID = 'paid', 'Оплачено'
    CANCELLED = 'cancelled', 'Отменено'


class Payment(models.Model):
    order = models.OneToOneField(
        Order, null=True, on_delete=models.SET_NULL, related_name='payment', verbose_name='Заказ'
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Сумма')
    payment_id = models.CharField(max_length=255, unique=True, db_index=True, verbose_name='ID Платежа')
    status = models.CharField(max_length=20, choices=StatusChoices.choices, default=StatusChoices.PENDING, verbose_name='Статус')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')

    class Meta:
        verbose_name = 'Платеж'
        verbose_name_plural = 'Платежи'
        permissions = [
            ('manage_payments', 'Может изменять платежи'),
        ]
        constraints = [
            models.CheckConstraint(condition=models.Q(amount__gt=0), name='amount_gt_0'),
            models.CheckConstraint(condition=models.Q(status__in=[choice.value for choice in StatusChoices]), name='status_in_status_choices'),
        ]
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        if self.order and self.order.order_id:
            return f'Заказ ({self.order.order_id}) - {self.amount} Р ({self.status})'
        return f'Платеж без заказа - {self.amount} Р ({self.status})'
