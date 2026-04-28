from types import SimpleNamespace
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
        cls.payment_webhook_url = reverse('payment:payment-webhook')

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

        ### Coupons ###

        # Данные для создания купонов
        time_start = timezone.now().date()
        time_end = (timezone.now() + timedelta(days=7)).date()

        # Создание трёх купонов
        cls.coupon = Coupon.objects.create(
            code='test-coupon-123321',
            valid_from=time_start,
            valid_to=time_end,
            discount=50,
            is_active=True
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
            coupon=cls.coupon,
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
            coupon=cls.coupon,
            total_price=Decimal('1.00'),
            status=StatusChoices.PENDING,
            yookassa_id=str(uuid4()),
        )

        cls.order_normal_new = Order.objects.create(
            order_id=uuid4(),
            user=cls.normal_user,
            full_name='Test full name',
            phone='+78005553535',
            address='Test address',
            city='Test city',
            coupon=cls.coupon,
            total_price=Decimal('1.00'),
            status=StatusChoices.PENDING,
            yookassa_id=str(uuid4()),
        )

        cls.order_normal_delivered = Order.objects.create(
            order_id=uuid4(),
            user=cls.normal_user,
            full_name='Test full name',
            phone='+78005553535',
            address='Test address',
            city='Test city',
            coupon=cls.coupon,
            total_price=Decimal('1.00'),
            status=StatusChoices.DELIVERED,
            yookassa_id=str(uuid4()),
        )

        # Создание элементов заказов
        OrderItem.objects.create(
            order=cls.order_normal,
            product=cls.product1,
            price=cls.product1.price,
            quantity=1,
        )
        OrderItem.objects.create(
            order=cls.order_admin,
            product=cls.product1,
            price=cls.product1.price,
            quantity=1,
        )
        OrderItem.objects.create(
            order=cls.order_admin,
            product=cls.product2,
            price=cls.product2.price,
            quantity=1,
        )
        OrderItem.objects.create(
            order=cls.order_normal_new,
            product=cls.product1,
            price=cls.product1.price,
            quantity=1,
        )
        OrderItem.objects.create(
            order=cls.order_normal_delivered,
            product=cls.product1,
            price=cls.product1.price,
            quantity=1,
        )

        # Переопределение цен
        cls.order_normal.total_price = cls.order_normal.total_price_after_discount
        cls.order_normal.save(update_fields=['total_price'])

        cls.order_admin.total_price = cls.order_admin.total_price_after_discount
        cls.order_admin.save(update_fields=['total_price'])

        cls.order_normal_new.total_price = cls.order_normal_new.total_price_after_discount
        cls.order_normal_new.save(update_fields=['total_price'])

        cls.order_normal_delivered.total_price = cls.order_normal_delivered.total_price_after_discount
        cls.order_normal_delivered.save(update_fields=['total_price'])

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
                return
        self.fail(f"Платёж с ID '{payment.payment_id}' не найден в ответе")

    def get_payment_detail_url_with_payment_id(self, payment_id):
        return reverse('payment:payment-detail', kwargs={'payment_id': str(payment_id)})
    
    def get_payment_create_url_with_order_id(self, order_id):
        return reverse('payment:payment-create', kwargs={'order_id': str(order_id)})

    def test_anon_user_cannot_get_payments_list(self):
        # Неправильное получение списка платежей и проверка
        invalid_anon_response = self.anon_client.get(self.payment_list_url)
        self.assertEqual(invalid_anon_response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_normal_user_cannot_get_payments_list(self):
        # Неправильное получение списка платежей и проверка
        invalid_normal_response = self.normal_client.get(self.payment_list_url)
        self.assertEqual(invalid_normal_response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_user_can_get_all_payments(self):
        # Получение списка платежей. где только его платеж и проверка
        normal_response = self.admin_client.get(self.payment_list_url)
        self.assertEqual(normal_response.status_code, status.HTTP_200_OK)

        # Проверка на наличие своего платежа
        self.check_contains_payment_in_payment_response(
            payment_response=normal_response, payment=self.payment_admin,
        )

        # Проверка на наличие чужого платежа
        self.check_contains_payment_in_payment_response(
            payment_response=normal_response, payment=self.payment_normal,
        )

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
            self.get_payment_create_url_with_order_id(order_id=self.order_normal.order_id),
        )
        self.assertEqual(invalid_anon_response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_normal_user_cannot_create_payment_with_invalid_order_id(self):
        # Неправильное создание платежа (с неверным order id) и проверка
        invalid_normal_response = self.normal_client.post(
            self.get_payment_create_url_with_order_id(order_id=str(uuid4())),
        )
        self.assertEqual(invalid_normal_response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(invalid_normal_response.data['error'], 'Такого заказа не существует')
    
    def test_normal_user_cannot_create_payment_with_other_order(self):
        # Неправильное создание платежа (с чужим заказом) и проверка
        invalid_normal_response = self.normal_client.post(
            self.get_payment_create_url_with_order_id(order_id=self.order_admin.order_id),
        )
        self.assertEqual(invalid_normal_response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(invalid_normal_response.data['error'], 'Вы не можете оплачивать чужой заказ')

    def test_admin_user_cannot_create_payment_for_order_where_payment_exists(self):
        # Неправильное создание платежа (с уже оплаченным заказом) и проверка
        invalid_admin_response = self.admin_client.post(
            self.get_payment_create_url_with_order_id(order_id=self.payment_admin.order.order_id),
        )
        self.assertEqual(invalid_admin_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(invalid_admin_response.data['error'], 'У этого заказа уже есть платеж')

    def test_admin_user_cannot_create_payment_with_invalid_order_status(self):
        # Неправильное создание платежа (с неправильным статусом) и проверка
        invalid_admin_response = self.admin_client.post(
            self.get_payment_create_url_with_order_id(
                order_id=self.order_normal_delivered.order_id,
            ),
        )
        self.assertEqual(invalid_admin_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(invalid_admin_response.data['error'], 'Оплата для этого заказа недоступна')

    def test_admin_user_can_create_payment_with_other_order(self):
        # Взятие товара для сравнения
        product_before = Product.objects.get(id=self.product1.pk)
        
        # Создание данных для подмены
        fake_payment_data = SimpleNamespace(
            id='yk_test_admin_create',
            confirmation=SimpleNamespace(
                confirmation_url='https://yoomoney.ru/checkout/payments/v2/contract?orderId=yk_test_admin_create'
            )
        )

        # Создание платежа (с чужим заказом) и проверка
        with patch('django_prod_shop.payment.services.YooPayment.create', return_value=fake_payment_data):
            created_admin_response = self.admin_client.post(
                self.get_payment_create_url_with_order_id(self.order_normal_new.order_id)
            )
        self.assertEqual(created_admin_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            created_admin_response.data['confirmation_url'],
            fake_payment_data.confirmation.confirmation_url,
        )

        # Проверка платежа
        self.assertTrue(Payment.objects.filter(payment_id='yk_test_admin_create').exists())
        new_payment = Payment.objects.get(payment_id='yk_test_admin_create')
        self.assertEqual(new_payment.status, PaymentStatusChoices.PENDING)

        # Проверка заказа
        self.assertEqual(Decimal(new_payment.amount), Decimal(self.order_normal_new.total_price))
        self.assertEqual(new_payment.order.order_id, self.order_normal_new.order_id)

        # Проверка товара
        product_after = Product.objects.get(id=self.product1.pk)
        self.assertEqual(product_after.reserved_quantity, product_before.reserved_quantity + 1)
        self.assertEqual(product_after.quantity, product_before.quantity)

    def test_normal_user_can_create_payment_with_his_own_order(self):
        # Взятие товара для сравнения
        product_before = Product.objects.get(id=self.product1.pk)

        # Создание данных для подмены
        fake_payment_data = SimpleNamespace(
            id='yk_test_normal_create',
            confirmation=SimpleNamespace(
                confirmation_url='https://yoomoney.ru/checkout/payments/v2/contract?orderId=yk_test_normal_create'
            )
        )

        # Создание платежа и проверка
        with patch('django_prod_shop.payment.services.YooPayment.create', return_value=fake_payment_data):
            created_normal_response = self.normal_client.post(
                self.get_payment_create_url_with_order_id(self.order_normal_new.order_id),
            )
        self.assertEqual(created_normal_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            created_normal_response.data['confirmation_url'],
            fake_payment_data.confirmation.confirmation_url,
        )

        # Проверка платежа
        self.assertTrue(Payment.objects.filter(payment_id='yk_test_normal_create').exists())
        new_payment = Payment.objects.get(payment_id='yk_test_normal_create')
        self.assertEqual(new_payment.status, PaymentStatusChoices.PENDING)

        # Проверка заказа
        self.assertEqual(Decimal(new_payment.amount), Decimal(self.order_normal_new.total_price))
        self.assertEqual(new_payment.order.order_id, self.order_normal_new.order_id)

        # Проверка товара
        product_after = Product.objects.get(id=self.product1.pk)
        self.assertEqual(product_after.reserved_quantity, product_before.reserved_quantity + 1)
        self.assertEqual(product_after.quantity, product_before.quantity)

    def test_webhook_returns_error_400_without_payment_id(self):
        # Неверные данные для вебхука (нет payment id)
        invalid_webhook_data = {'object': {
            'status': 'succeeded',
        }}

        # Неправильная работа с вебхуком и проверка
        invalid_webhook_response = self.client.post(
            self.payment_webhook_url,
            data=invalid_webhook_data,
            format='json',
        )
        self.assertEqual(invalid_webhook_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(invalid_webhook_response.data['error'], 'Нет ID платежа')

    def test_webhook_returns_error_404_with_invalid_payment_id(self):
        # Неверные данные для вебхука (неверный payment id)
        invalid_webhook_data = {'object': {
            'id': 'invalid_payment_id',
            'status': 'succeeded',
        }}

        # Неправильная работа с вебхуком и проверка
        invalid_webhook_response = self.client.post(
            self.payment_webhook_url,
            data=invalid_webhook_data,
            format='json',
        )
        self.assertEqual(invalid_webhook_response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(invalid_webhook_response.data['error'], 'Платеж не найден')
    
    def test_webhook_returns_ignored_with_invalid_status(self):
        # Неверные данные для вебхука (неверный статус)
        invalid_webhook_data = {'object': {
            'id': self.payment_normal.payment_id,
            'status': 'invalid_status',
        }}

        # Неправильная работа с вебхуком и проверка
        invalid_webhook_response = self.client.post(
            self.payment_webhook_url,
            data=invalid_webhook_data,
            format='json',
        )
        self.assertEqual(invalid_webhook_response.status_code, status.HTTP_200_OK)
        self.assertEqual(invalid_webhook_response.data['status'], 'ignored')

    def test_webhook_confirms_payment(self):
        # Взятие товара для сравнения
        product_before = Product.objects.get(id=self.product1.pk)

        # Данные для вебхука
        webhook_data = {'object': {
            'id': self.payment_normal.payment_id,
            'status': 'succeeded',
        }}

        # Работа с вебхуком и проверка
        webhook_response = self.client.post(
            self.payment_webhook_url,
            data=webhook_data,
            format='json',
        )
        self.assertEqual(webhook_response.status_code, status.HTTP_200_OK)

        # Проверка платежа и заказа
        self.payment_normal.refresh_from_db()
        self.order_normal.refresh_from_db()
        product_after = Product.objects.get(pk=self.product1.pk)
        
        # Проверка на изменение заказа, платежа и продукта
        self.assertEqual(self.payment_normal.status, PaymentStatusChoices.PAID)
        self.assertEqual(self.order_normal.status, StatusChoices.PAID)
        self.assertEqual(product_after.quantity, product_before.quantity - 1)
        self.assertEqual(product_after.reserved_quantity, product_before.reserved_quantity - 1)
    
    def test_webhook_cancels_payment(self):
        # Взятие товара для сравнения
        product_before = Product.objects.get(id=self.product1.pk)

        # Данные для вебхука
        webhook_data = {'object': {
            'id': self.payment_normal.payment_id,
            'status': 'canceled',
        }}

        # Работа с вебхуком и проверка
        webhook_response = self.client.post(
            self.payment_webhook_url,
            data=webhook_data,
            format='json',
        )
        self.assertEqual(webhook_response.status_code, status.HTTP_200_OK)

        # Проверка платежа и заказа
        self.payment_normal.refresh_from_db()
        self.order_normal.refresh_from_db()
        product_after = Product.objects.get(pk=self.product1.pk)
        
        # Проверка на изменение заказа, платежа и продукта
        self.assertEqual(self.payment_normal.status, PaymentStatusChoices.CANCELLED)
        self.assertEqual(self.order_normal.status, StatusChoices.CANCELLED)
        self.assertEqual(product_after.quantity, product_before.quantity)
        self.assertEqual(product_after.reserved_quantity, product_before.reserved_quantity - 1)
    
    def test_webhook_confirm_is_idempotent(self):
        # Взятие товара для сравнения
        product_before = Product.objects.get(id=self.product1.pk)

        # Данные для вебхука
        webhook_data = {'object': {
            'id': self.payment_normal.payment_id,
            'status': 'succeeded',
        }}

        # Одинаковые запросы к вебхуку и проверка
        first_response = self.client.post(
            self.payment_webhook_url,
            data=webhook_data,
            format='json',
        )
        second_response = self.client.post(
            self.payment_webhook_url,
            data=webhook_data,
            format='json',
        )
        self.assertEqual(first_response.status_code, status.HTTP_200_OK)
        self.assertEqual(second_response.status_code, status.HTTP_200_OK)

        # Обновление заказа и платежа
        self.payment_normal.refresh_from_db()
        self.order_normal.refresh_from_db()
        product_after = Product.objects.get(pk=self.product1.pk)

        # Проверка на изменение заказа, платежа и продукта
        self.assertEqual(self.payment_normal.status, PaymentStatusChoices.PAID)
        self.assertEqual(self.order_normal.status, StatusChoices.PAID)
        self.assertEqual(product_after.quantity, product_before.quantity - 1)
        self.assertEqual(product_after.reserved_quantity, product_before.reserved_quantity - 1)

    def test_webhook_cancel_is_idempotent(self):
        # Взятие товара для сравнения
        product_before = Product.objects.get(id=self.product1.pk)

        # Данные для вебхука
        webhook_data = {'object': {
            'id': self.payment_normal.payment_id,
            'status': 'canceled',
        }}

        # Одинаковые запросы к вебхуку и проверка
        first_response = self.client.post(
            self.payment_webhook_url,
            data=webhook_data,
            format='json',
        )
        second_response = self.client.post(
            self.payment_webhook_url,
            data=webhook_data,
            format='json',
        )
        self.assertEqual(first_response.status_code, status.HTTP_200_OK)
        self.assertEqual(second_response.status_code, status.HTTP_200_OK)

        # Обновление заказа и платежа
        self.payment_normal.refresh_from_db()
        self.order_normal.refresh_from_db()
        product_after = Product.objects.get(pk=self.product1.pk)

        # Проверка на изменение заказа, платежа и продукта
        self.assertEqual(self.payment_normal.status, PaymentStatusChoices.CANCELLED)
        self.assertEqual(self.order_normal.status, StatusChoices.CANCELLED)
        self.assertEqual(product_after.quantity, product_before.quantity)
        self.assertEqual(product_after.reserved_quantity, product_before.reserved_quantity - 1)
