from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError


class Coupon(models.Model):
    code = models.CharField(max_length=100, verbose_name='Купон', unique=True)
    discount = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(100)], verbose_name='Скидка (%)'
    )
    valid_from = models.DateField(verbose_name='Дата начала работы')
    valid_to = models.DateField(verbose_name='Дата конца работы')
    is_active = models.BooleanField(default=True, verbose_name='Статус')
    
    class Meta:
        verbose_name = 'Купон'
        verbose_name_plural = 'Купоны'
        permissions = [
            ('manage_coupons', 'Может изменять купоны'),
        ]
        ordering = ['-valid_from']
        indexes = [
            models.Index(fields=['is_active']),
            models.Index(fields=['valid_from']),
        ]

    def __str__(self):
        return f'Купон {self.code}. Скидка {self.discount}%'
    
    def clean(self):
        if self.valid_to <= self.valid_from:
            raise ValidationError('Дата окончания должна быть позже даты начала')
