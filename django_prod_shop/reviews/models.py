from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator

from django_prod_shop.products.models import Product


user_model = get_user_model()


class Review(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name='Товар')
    user = models.ForeignKey(user_model, on_delete=models.CASCADE, verbose_name='Пользователь')
    comment = models.TextField(blank=True, verbose_name='Комментарий')
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)], verbose_name='Рейтинг'
    )
