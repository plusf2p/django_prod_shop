import uuid

from django.core.validators import MaxValueValidator, MinValueValidator
from django.contrib.auth import get_user_model
from django.db import models
from decimal import Decimal

from django_prod_shop.products.models import Product


user = get_user_model()


class Order(models.Model):
    class StatusChoices(models.TextChoices):
        PENDING = 'pending', 'В процессе'
        PAID = 'paid', 'Оплачено'
        DELIVERED = 'delivered', 'Доставлено'
        CANCELLED = 'cancelled', 'Отменено'

    order_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        user, null=True, related_name='orders', on_delete=models.SET_NULL, verbose_name='Пользователь'
    )
    full_name = models.CharField(max_length=250, verbose_name='Полное имя')
    phone = models.CharField(max_length=20, verbose_name='Телефон')
    address = models.CharField(max_length=250, verbose_name='Адрес')
    city = models.CharField(max_length=100, verbose_name='Город')
    discount = models.IntegerField(
        default=0, validators=[MaxValueValidator(100), MinValueValidator(0)], verbose_name='Скидка (%)'
    )
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='Общая стоимость')
    status = models.CharField(
        max_length=20, choices=StatusChoices.choices, default=StatusChoices.PENDING, verbose_name='Статус'
    )
    yookassa_id = models.CharField(max_length=255, verbose_name='ID Платежа YooKassa')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')

    class Meta:
        verbose_name_plural = 'Заказы'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
        ]

    def __str__(self):
        return f'Заказ: {self.user}. ID: {self.pk}'
    
    @property
    def total_price_before_discount(self):
        return sum((item.cost for item in self.items.all()), Decimal('0.00'))

    @property
    def discount_price(self):
        total_cost = self.total_price_before_discount
        if self.discount:
            return total_cost * (Decimal(self.discount) / Decimal('100'))
        return Decimal('0.00')

    @property
    def total_price_after_discount(self):
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

    def __str__(self):
        return f'{self.order} | {self.product} x ({self.quantity})'

    @property
    def cost(self):
        return self.price * self.quantity
