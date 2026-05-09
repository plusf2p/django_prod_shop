import uuid
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import models

from django_prod_shop.products.models import Product
from django_prod_shop.coupons.models import Coupon


user = get_user_model()


class StatusChoices(models.TextChoices):
    PENDING = 'pending', 'В процессе'
    PAID = 'paid', 'Оплачено'
    DELIVERED = 'delivered', 'Доставлено'
    CANCELLED = 'cancelled', 'Отменено'


class Order(models.Model):
    order_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        user, null=True, related_name='orders', on_delete=models.SET_NULL, verbose_name='Пользователь'
    )
    full_name = models.CharField(max_length=250, verbose_name='Полное имя')
    phone = models.CharField(max_length=20, verbose_name='Телефон')
    address = models.CharField(max_length=250, verbose_name='Адрес')
    city = models.CharField(max_length=100, verbose_name='Город')
    coupon = models.ForeignKey(Coupon, null=True, blank=True, on_delete=models.SET_NULL, verbose_name='Купон')
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'), verbose_name='Общая стоимость')
    status = models.CharField(
        max_length=20, choices=StatusChoices.choices, default=StatusChoices.PENDING, verbose_name='Статус'
    )
    yookassa_id = models.CharField(max_length=255, blank=True, default='', verbose_name='ID Платежа YooKassa')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')

    class Meta:
        verbose_name_plural = 'Заказы'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['created_at']),
        ]
        permissions = [
            ('manage_orders', 'Может изменять заказы'),
        ]

    def __str__(self) -> str:
        return f'Заказ: {self.user}. ID: {self.pk}'
    
    @property
    def total_price_before_discount(self) -> Decimal:
        return sum((item.cost for item in self.items.all()), Decimal('0.00'))

    @property
    def discount_price(self) -> Decimal:
        total_cost = self.total_price_before_discount
        if self.coupon_id:
            return total_cost * (Decimal(self.coupon.discount) / Decimal('100'))
        return Decimal('0.00')

    @property
    def total_price_after_discount(self) -> Decimal:
        return self.total_price_before_discount - self.discount_price


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order, related_name='items', on_delete=models.CASCADE, verbose_name='Заказ'
    )
    product = models.ForeignKey(
        Product, related_name='order_items', on_delete=models.PROTECT, verbose_name='Товар'
    )
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Цена')
    quantity = models.PositiveIntegerField(default=1, verbose_name='Количество')

    class Meta:
        verbose_name_plural = 'Товары заказа'
        constraints = [
            models.UniqueConstraint(fields=['order', 'product'], name='unique_order_product'),
            models.CheckConstraint(condition=models.Q(price__gte=0), name='order_item_price_gte_0'),
        ]
        

    def __str__(self) -> str:
        return f'{self.order} | {self.product} x ({self.quantity})'

    @property
    def cost(self) -> Decimal:
        return self.price * self.quantity
