from unittest.mock import patch
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
from django_prod_shop.payment.models import Payment, StatusChoices as PaymentStatusChoices


user_model = get_user_model()


class PaymentAPITest(APITestCase):
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

        # Создание пользователя для неправильного заказа
        cls.invalid_order_user_data = {
            'email': 'new_test_user_without_cart@mail.ru',
            'password': '123123123',
        }
        cls.invalid_order_user = user_model.objects.create_user(
            email=cls.invalid_order_user_data['email'], 
            password=cls.invalid_order_user_data['password'],
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
        cls.payment_list_url = reverse('payment:payment-list')

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
            yookassa_id=str(uuid4()),
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
            yookassa_id=str(uuid4()),
        )

        cls.order_normal_new = Order.objects.create(
            order_id=uuid4(),
            user=cls.normal_user,
            full_name='Test full name',
            phone='+78005553535',
            address='Test address',
            city='Test city',
            coupon=cls.coupon1,
            total_price=Decimal('1.00'),
            status=StatusChoices.PENDING,
            yookassa_id=str(uuid4()),
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
        cls.order_item_normal_new = OrderItem.objects.create(
            order=cls.order_normal_new,
            product=cls.product1,
            price=cls.product1.price,
            quantity=1,
        )

        # Переопределение цен
        cls.order_normal.total_price = cls.order_normal.total_price_after_discount
        cls.order_normal.save(update_fields=['total_price'])

        cls.order_admin.total_price = cls.order_admin.total_price_after_discount
        cls.order_admin.save(update_fields=['total_price'])

        ### Payments ###
        cls.payment_normal = Payment.objects.create(
            order=cls.order_normal,
            amount=cls.order_normal.total_price_after_discount,
            payment_id=str(uuid4()),
            status=PaymentStatusChoices.PENDING,
        )

        cls.payment_admin = Payment.objects.create(
            order=cls.order_admin,
            amount=cls.order_admin.total_price_after_discount,
            payment_id=str(uuid4()),
            status=PaymentStatusChoices.PAID,
        )

    def setUp(self):
        cache.clear()
        self.admin_client = APIClient()
        self.normal_client = APIClient()
        self.anon_client = APIClient()

        # Авторизация админа, и двух обычных пользователей
        self.normal_client.force_authenticate(user=self.normal_user)
        self.admin_client.force_authenticate(user=self.admin_user)

    def check_payment_in_payment_data(self, payment_data, payment):
        self.assertEqual(payment_data['order']['order_id'], str(payment.order.order_id))
        self.assertEqual(Decimal(payment_data['amount']), Decimal(payment.amount))
        self.assertEqual(payment_data['status'], payment.status)


    def check_contains_payment_in_payment_response(self, payment_response, payment):
        for payment_item in payment_response.data:
            if payment_item['payment_id'] == str(payment.payment_id):
                self.check_payment_in_payment_data(payment_data=payment_item, payment=payment)
                return True
        return False

    def get_payment_detail_url_with_payment_id(self, payment_id):
        return reverse('payment:payment-detail', kwargs={'payment_id': str(payment_id)})
    
    def get_payment_create_url_with_order_id(self, order_id):
        return reverse('payment:payment-create', kwargs={'order_id': str(order_id)})

    def test_anon_user_cannot_get_payments_list(self):
        # Неправильное получение списка платежей и проверка
        invalid_anon_response = self.anon_client.get(self.payment_list_url)
        self.assertEqual(invalid_anon_response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_nomal_user_cannot_get_payments_list(self):
        # Неправильное получение списка платежей и проверка
        invalid_normal_response = self.normal_client.get(self.payment_list_url)
        self.assertEqual(invalid_normal_response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_user_can_get_all_payments(self):
        # Получение списка платежей. где только его платеж и проверка
        normal_response = self.admin_client.get(self.payment_list_url)
        self.assertEqual(normal_response.status_code, status.HTTP_200_OK)

        # Проверка на наличие своего платежа
        self.assertTrue(self.check_contains_payment_in_payment_response(
            payment_response=normal_response, payment=self.payment_admin,
        ))

        # Проверка на наличие чужого платежа
        self.assertTrue(self.check_contains_payment_in_payment_response(
            payment_response=normal_response, payment=self.payment_normal,
        ))

    def test_anon_user_cannot_get_payment_detail(self):
        # Неправильное получение платежа и проверка
        invalid_anon_response = self.anon_client.get(
            self.get_payment_detail_url_with_payment_id(payment_id=self.payment_normal.payment_id),
        )
        self.assertEqual(invalid_anon_response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_normal_user_cannot_get_other_payment_detail(self):
        # Получение чужого платежа и проверка
        invalid_normal_response = self.normal_client.get(
            self.get_payment_detail_url_with_payment_id(payment_id=self.payment_admin.payment_id),
        )
        self.assertEqual(invalid_normal_response.status_code, status.HTTP_404_NOT_FOUND)

    def test_normal_user_can_get_his_own_payment_detail(self):
        # Получение своего платежа и проверка
        detail_normal_response = self.normal_client.get(
            self.get_payment_detail_url_with_payment_id(payment_id=self.payment_normal.payment_id),
        )
        self.assertEqual(detail_normal_response.status_code, status.HTTP_200_OK)

        # Проверка на совпадение своего платежа
        self.check_payment_in_payment_data(
            payment_data=detail_normal_response.data, payment=self.payment_normal,
        )
    
    def test_admin_user_can_get_other_payment_detail(self):
        # Получение чужого платежа и проверка
        detail_admin_response = self.admin_client.get(
            self.get_payment_detail_url_with_payment_id(payment_id=self.payment_normal.payment_id),
        )
        self.assertEqual(detail_admin_response.status_code, status.HTTP_200_OK)

        # Проверка на совпадение чужого платежа
        self.check_payment_in_payment_data(
            payment_data=detail_admin_response.data, payment=self.payment_normal,
        )
    
    def test_anon_user_cannot_create_payment(self):
        # Неправильное создание платежа и проверка
        invalid_anon_response = self.anon_client.post(
            self.get_payment_create_url_with_order_id(order_id=self.payment_normal.order.order_id),
        )
        self.assertEqual(invalid_anon_response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_normal_user_cannot_create_payment_with_invalid_order_id(self):
        # Неправильное создание платежа (с неверным order id) и проверка
        invalid_normal_response = self.normal_client.post(
            self.get_payment_create_url_with_order_id(order_id=str(uuid4())),
        )
        self.assertEqual(invalid_normal_response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_admin_user_cannot_create_payment_with_other_order(self):
        # Неправильное создание платежа (с чужим заказом) и проверка
        invalid_normal_response = self.admin_client.post(
            self.get_payment_create_url_with_order_id(order_id=self.payment_normal.order.order_id),
        )
        self.assertEqual(invalid_normal_response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_normal_user_can_create_payment_with_his_own_order(self):
        # Создание платежа и проверка
        create_normal_response = self.normal_client.post(
            self.get_payment_create_url_with_order_id(order_id=self.order_item_normal_new.order.order_id),
        )
        self.assertEqual(create_normal_response.status_code, status.HTTP_201_CREATED)

        # Упрощение обращения
        data = create_normal_response.data

        # Проверка на наличие нового платежа
        self.assertTrue(Payment.objects.filter(payment_id=data['payment_id']).exists())
        new_payment = Payment.objects.get(payment_id=data['payment_id'])
        self.assertEqual(data['payment_id'], new_payment.payment_id)
