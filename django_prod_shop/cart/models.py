from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import models

from django_prod_shop.coupons.models import Coupon
from django_prod_shop.products.models import Product


user = get_user_model()


class Cart(models.Model):
    user = models.OneToOneField(
        user, related_name='cart', on_delete=models.CASCADE,
        null=True, blank=True, verbose_name='Пользователь'
    )
    session_key = models.CharField(max_length=50, null=True, blank=True, verbose_name='Ключ сессии', unique=True)
    coupon = models.ForeignKey(Coupon, null=True, blank=True, on_delete=models.SET_NULL, verbose_name='Купон')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')

    @property
    def total_price(self):
        total = sum((item.total_price for item in self.cart_items.all()), Decimal('0'))
        if self.coupon_id:
            total = total - total * (Decimal(str(self.coupon.discount)) / Decimal('100'))
        return total

    @property
    def total_quantity(self):
        return sum(item.quantity for item in self.cart_items.all())

    class Meta:
        verbose_name_plural = 'Корзина'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        if self.user:
            return f"Корзина ({self.pk}) : {self.user.username}"
        return f"Корзина ({self.pk}) : Аноним"


class CartItem(models.Model):
    cart = models.ForeignKey(
        Cart, related_name='cart_items', on_delete=models.CASCADE, verbose_name='Корзина'
    )
    product = models.ForeignKey(
        Product, related_name='cart_item_product', on_delete=models.CASCADE, verbose_name='Товар'
    )
    quantity = models.PositiveIntegerField(verbose_name='Количество')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')

    @property
    def total_price(self):
        return self.product.price * self.quantity

    class Meta:
        verbose_name_plural = 'Товары в корзине'
        ordering = ['cart']
        constraints = [
            models.UniqueConstraint(fields=['cart', 'product'], name='unique_cart_product'),
            models.CheckConstraint(condition=models.Q(quantity__gt=0), name='quantity_gt_0'),
        ]

    def __str__(self):
        return f'{self.product} ({self.quantity})'
