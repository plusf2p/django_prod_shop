from datetime import timedelta
from uuid import uuid4

from django.core.cache import cache
from django.core.management import call_command
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.urls import reverse

from rest_framework.test import APITestCase, APIClient
from rest_framework import status

from django_prod_shop.orders.models import Order, OrderItem, StatusChoices
from django_prod_shop.coupons.models import Coupon
from django_prod_shop.products.models import Category, Product


user_model = get_user_model()


class CartAPITest(APITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        
        # Создание ролей
        call_command('create_groups')
        
        ### Users ####

        # Создание обычного пользователя
        cls.normal_user_data = {
            'email': 'test_user1@mail.ru',
            'password': 'test_user1_password!',
        }
        cls.normal_user = user_model.objects.create_user(
            email=cls.normal_user_data['email'], 
            password=cls.normal_user_data['password'],
            is_active=True,
        )

        # Создание админа (суперюзера)
        cls.admin_user_data = {
            'email': 'admin@mail.ru',
            'password': 'admin_password!',
        }
        cls.admin_user = user_model.objects.create_superuser(
            email=cls.admin_user_data['email'], 
            password=cls.admin_user_data['password'],
            is_active=True,
        )

        # Объявление url
        cls.orders_list = reverse('orders:orders-list')

        ### Products ###

        # Создание стартовой категории
        cls.category = Category.objects.create(
            title='Test category', description='test description', slug='test-category'
        )
        
        # Создание двух стартовых товаров
        cls.product1 = Product.objects.create(
            title='Test title of first product', category=cls.category, quantity=10, reserved_quantity=5, 
            description='1', slug='test-title-of-first-product', price=800, is_active=True,
        )
        cls.product2 = Product.objects.create(
            title='Test title of second product', category=cls.category, quantity=100, reserved_quantity=10, 
            description='2', slug='test-title-of-second-product', price=400, is_active=True,
        )
        cls.product_inactive = Product.objects.create(
            title='Test title of inactive product', category=cls.category, quantity=100, reserved_quantity=10, 
            description='inative', slug='test-title-of-inactive-product', price=200, is_active=False,
        )

        ### Coupons ###

        # Данные для создания купонов
        time_start = timezone.now().date()
        time_end = (timezone.now() + timedelta(days=7)).date()

        # Создание трёх купонов
        cls.coupon1 = Coupon.objects.create(
            code='test-coupon-123321',
            valid_from=time_start,
            valid_to=time_end,
            discount=50,
            is_active=True
        )
        cls.coupon2 = Coupon.objects.create(
            code='test-coupon-321123',
            valid_from=time_start,
            valid_to=time_end,
            discount=25,
            is_active=True
        )
        cls.coupon_inactive = Coupon.objects.create(
            code='test-coupon-inactive',
            valid_from=time_start,
            valid_to=time_end,
            discount=50,
            is_active=False
        )
        cls.coupon_future = Coupon.objects.create(
            code='test-coupon-future',
            valid_from=time_start + timedelta(days=10),
            valid_to=time_start + timedelta(days=11),
            discount=50,
            is_active=True,
        )
        cls.coupon_past = Coupon.objects.create(
            code='test-coupon-past',
            valid_from=time_start - timedelta(days=11),
            valid_to=time_start - timedelta(days=10),
            discount=50,
            is_active=True,
        )

        ### Orders ###

        # Создание заказа
        cls.order_normal = Order.objects.create(
            order_id=uuid4(),
            user=cls.normal_user,
            full_name='Test full name',
            phone='+78005553535',
            address='Test address',
            city='Test city',
            coupon=cls.coupon1,
            total_price=1,
            status=StatusChoices.PENDING,
            yookasssa_id=uuid4(),
        )

        # Создание элемента заказа
        cls.order_item_normal1 = OrderItem.objects.create(
            order=cls.order_normal,
            product=cls.product1,
            price=cls.product1.price,
            quantity=1,
        )

        # Переопределение цены
        cls.order_normal.total_price = cls.order_normal.total_price_after_discount
        cls.order_normal.save()

    def setUp(self):
        cache.clear()
        self.admin_client = APIClient()
        self.normal_client = APIClient()
        self.anon_client = APIClient()

        # Авторизация админа и обычного пользователя
        self.normal_client.force_authenticate(user=self.normal_user)
        self.admin_client.force_authenticate(user=self.admin_user)
    
    def get_order_detail_url_with_order_id(self, order_id):
        return reverse('orders:orders-detail', kwargs={'order_id': order_id})

    def test_anon_user_cannot_get_orders_detail(self):
        pass