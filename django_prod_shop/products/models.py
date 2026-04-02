from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse


class Category(models.Model):
    title = models.CharField(max_length=150, verbose_name='Название')
    description = models.TextField(blank=True, verbose_name='Описание')
    slug = models.SlugField(unique=True, verbose_name='Слаг')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['created_at']),
        ]
        permissions = [
            ('manage_categories', 'Может изменять категории'),
        ]


class Product(models.Model):
    title = models.CharField(max_length=150, verbose_name='Название')
    category = models.ForeignKey(
        Category, null=True, related_name='products',
        on_delete=models.SET_NULL, verbose_name='Категория'
    )
    slug = models.SlugField(unique=True, verbose_name='Слаг')
    quantity = models.PositiveIntegerField(default=0, verbose_name='Количество')
    reserved_quantity = models.PositiveIntegerField(default=0, verbose_name='Зарезервировано')
    image = models.ImageField(
        upload_to='img/products/', default='img/products/hero-bg.jpg',
        null=True, blank=True, verbose_name='Картинка'
    )
    description = models.TextField(blank=True, verbose_name='Описание')
    price = models.DecimalField(max_digits=9, decimal_places=2, verbose_name='Цена')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    is_active = models.BooleanField(default=True, verbose_name='Статус активности')

    class Meta:
        verbose_name = 'Товар'
        verbose_name_plural = 'Товары'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['created_at']),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(price__gte=0),
                name='product_price_gte_0'
            ),
            models.CheckConstraint(
                condition=models.Q(quantity__gte=0),
                name='product_quantity_gte_0'
            ),
            models.CheckConstraint(
                condition=models.Q(reserved_quantity__gte=0),
                name='reserved_quantity_gte_0'
            ),
            models.CheckConstraint(
                condition=models.Q(quantity__gte=models.F('reserved_quantity')),
                name='product_reserved_quantity_lte_quantity',
            ),
        ]
        permissions = [
            ('manage_products', 'Может изменять товары'),
        ]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('shop_detail', kwargs={'slug': self.slug})

    def clean(self):
        if self.reserved_quantity > self.quantity:
            raise ValidationError('Резерв не может превышать общее количество')
