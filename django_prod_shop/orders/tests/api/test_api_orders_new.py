from datetime import timedelta
from decimal import Decimal
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
from django_prod_shop.cart.models import Cart, CartItem
from django_prod_shop.products.models import Category, Product


user_model = get_user_model()


class OrdersAPITest(APITestCase):
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
        cls.orders_list_url = reverse('orders:orders-list')

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

        ### Cart ###

        # Создание корзины
        cls.cart_normal = Cart.objects.create(
            user=cls.normal_user,
            coupon=cls.coupon1,
        )

        # Создание элеиентов корзины
        cls.cart_item_normal1 = CartItem.objects.create(
            cart=cls.cart_normal,
            product=cls.product1,
            quantity=1,
        )

        cls.cart_item_normal2 = CartItem.objects.create(
            cart=cls.cart_normal,
            product=cls.product2,
            quantity=2,
        )

        ### Orders ###

        # Создание заказов
        cls.order_normal = Order.objects.create(
            order_id=uuid4(),
            user=cls.normal_user,
            full_name='Test full name',
            phone='+78005553535',
            address='Test address',
            city='Test city',
            coupon=cls.coupon1,
            total_price=Decimal('1.00'),
            status=StatusChoices.PENDING,
            yookassa_id=uuid4(),
        )

        cls.order_admin = Order.objects.create(
            order_id=uuid4(),
            user=cls.admin_user,
            full_name='Test full name admin',
            phone='+79999999999',
            address='Test address admin',
            city='Test city admin',
            coupon=cls.coupon2,
            total_price=Decimal('1.00'),
            status=StatusChoices.DELIVERED,
            yookassa_id=uuid4(),
        )

        # Создание элементов заказов
        cls.order_item_normal = OrderItem.objects.create(
            order=cls.order_normal,
            product=cls.product1,
            price=cls.product1.price,
            quantity=1,
        )
        cls.order_item_admin1 = OrderItem.objects.create(
            order=cls.order_admin,
            product=cls.product1,
            price=cls.product1.price,
            quantity=1,
        )
        cls.order_item_admin2 = OrderItem.objects.create(
            order=cls.order_admin,
            product=cls.product2,
            price=cls.product2.price,
            quantity=1,
        )

        # Переопределение цен
        cls.order_normal.total_price = cls.order_normal.total_price_after_discount
        cls.order_normal.save()

        cls.order_admin.total_price = cls.order_admin.total_price_after_discount
        cls.order_admin.save()

    def setUp(self):
        cache.clear()
        self.admin_client = APIClient()
        self.normal_client = APIClient()
        self.anon_client = APIClient()

        # Авторизация админа и обычного пользователя
        self.normal_client.force_authenticate(user=self.normal_user)
        self.admin_client.force_authenticate(user=self.admin_user)
    
    def get_order_detail_url_with_order_id(self, order_id):
        return reverse('orders:orders-detail', kwargs={'order_id': str(order_id)})

    def check_order_in_order_data(self, order_data, order):
        self.assertEqual(order_data['user'], order.user.email)
        self.assertEqual(order_data['phone'], order.phone)
        self.assertEqual(order_data['address'], order.address)
        self.assertEqual(order_data['city'], order.city)
        self.assertEqual(order_data['coupon'], order.coupon.code)
        self.assertEqual(Decimal(order_data['total_price']), Decimal(order.total_price))
        self.assertEqual(order_data['status'], order.status)
        self.assertEqual(Decimal(order_data['total_price_before_discount']), Decimal(order.total_price_before_discount))
        self.assertEqual(Decimal(order_data['discount_price']), Decimal(order.discount_price))
        self.assertEqual(Decimal(order_data['total_price_after_discount']), Decimal(order.total_price_after_discount))

    def check_contains_order_in_order_response(self, order_response, order):
        for order_item in order_response.data:
            if order_item['order_id'] == str(order.order_id):
                self.check_order_in_order_data(order_data=order_item, order=order)
                return True
        return False

    def test_anon_user_cannot_get_orders_list(self):
        # Неправильное получение списка заказов и проверка
        invalid_anon_response = self.anon_client.get(self.orders_list_url)
        self.assertEqual(invalid_anon_response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_normal_user_can_get_his_own_orders_in_orders_list(self):
        # Получение списка заказов и проверка
        list_normal_response = self.normal_client.get(self.orders_list_url)
        self.assertEqual(list_normal_response.status_code, status.HTTP_200_OK)

        # Проверка на наличие своего заказа в списке
        self.assertTrue(
            self.check_contains_order_in_order_response(
                order_response=list_normal_response,
                order=self.order_normal,
            )
        )
    
    def test_normal_user_cannot_get_other_orders_in_orders_list(self):
        # Получение списка заказов и проверка
        list_normal_response = self.normal_client.get(self.orders_list_url)
        self.assertEqual(list_normal_response.status_code, status.HTTP_200_OK)

        # Проверка на отсутсвтие чужого зкаказа в списке
        self.assertFalse(
            self.check_contains_order_in_order_response(
                order_response=list_normal_response,
                order=self.order_admin,
            )
        )

    def test_admin_user_can_get_all_orders(self):
        # Получение списка заказов и проверка
        admin_normal_response = self.admin_client.get(self.orders_list_url)
        self.assertEqual(admin_normal_response.status_code, status.HTTP_200_OK)

        # Проверка на наличие всехх заказов в списке
        self.assertTrue(
            self.check_contains_order_in_order_response(
                order_response=admin_normal_response,
                order=self.order_normal,
            )
        )
        self.assertTrue(
            self.check_contains_order_in_order_response(
                order_response=admin_normal_response,
                order=self.order_admin,
            )
        )

    def test_anon_user_cannot_get_order_detail(self):
        # Неправильное получение заказа и проверка
        invalid_anon_response = self.anon_client.get(
            self.get_order_detail_url_with_order_id(order_id=self.order_normal.order_id),
        )
        self.assertEqual(invalid_anon_response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_normal_user_can_get_his_own_order_detail(self):
        # Получение своего заказа и проверка
        detail_normal_response = self.normal_client.get(
            self.get_order_detail_url_with_order_id(order_id=self.order_normal.order_id),
        )
        self.assertEqual(detail_normal_response.status_code, status.HTTP_200_OK)

        # Проверка на совпадение заказа из ответа
        self.check_order_in_order_data(
            order_data=detail_normal_response.data, order=self.order_normal,
        )
    
    def test_normal_user_cannot_get_other_order_detail(self):
        # Неправильное получение чужого заказа и проверка
        invalid_normal_response = self.normal_client.get(
            self.get_order_detail_url_with_order_id(order_id=self.order_admin.order_id),
        )
        self.assertEqual(invalid_normal_response.status_code, status.HTTP_404_NOT_FOUND)

    def test_admin_user_can_get_other_order_detail(self):
        # Получение своего заказа и проверка
        detail_admin_response = self.admin_client.get(
            self.get_order_detail_url_with_order_id(order_id=self.order_normal.order_id),
        )
        self.assertEqual(detail_admin_response.status_code, status.HTTP_200_OK)

        # Проверка на совпадение заказа из ответа
        self.check_order_in_order_data(
            order_data=detail_admin_response.data, order=self.order_normal,
        )

    def test_anon_user_cannot_create_order(self):
        # Неправильное создание заказа и проверка
        invalid_anon_response = self.anon_client.post(self.orders_list_url)
        self.assertEqual(invalid_anon_response.status_code, status.HTTP_401_UNAUTHORIZED)
