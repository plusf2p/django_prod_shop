from unittest.mock import patch, MagicMock
from datetime import timedelta
from uuid import uuid4, UUID
from decimal import Decimal
from typing import Any

from django.core.management import call_command
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.cache import cache
from django.utils import timezone
from django.urls import reverse

from rest_framework.test import APITestCase, APIClient
from rest_framework.response import Response
from rest_framework import status

from django_prod_shop.orders.models import Order, OrderItem, StatusChoices
from django_prod_shop.products.models import Category, Product
from django_prod_shop.cart.models import Cart, CartItem
from django_prod_shop.coupons.models import Coupon


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

        # Создание менеджера
        cls.manager_user_data = {
            'email': 'test_manager1@mail.ru',
            'password': 'test_manager1_password!',
        }
        cls.manager_user = user_model.objects.create_user(
            email=cls.manager_user_data['email'], 
            password=cls.manager_user_data['password'],
            is_active=True,
        )
        # Назначение роли менеджера менеджеру
        group, _ = Group.objects.get_or_create(name='Manager')
        cls.manager_user.groups.add(group)

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
        cls.order_normal.save(update_fields=['total_price'])

        cls.order_admin.total_price = cls.order_admin.total_price_after_discount
        cls.order_admin.save(update_fields=['total_price'])

    def setUp(self) -> None:
        cache.clear()
        self.admin_client = APIClient()
        self.normal_client = APIClient()
        self.manager_client = APIClient()
        self.anon_client = APIClient()
        self.invalid_order_client = APIClient()

        # Авторизация админа, и двух обычных пользователей
        self.normal_client.force_authenticate(user=self.normal_user)
        self.manager_client.force_authenticate(user=self.manager_user)
        self.invalid_order_client.force_authenticate(user=self.invalid_order_user)
        self.admin_client.force_authenticate(user=self.admin_user)
    
    def get_order_detail_url_with_order_id(self, order_id: UUID) -> str:
        return reverse('orders:orders-detail', kwargs={'order_id': str(order_id)})

    def get_order_status_change_url_with_order_id(self, order_id: UUID) -> str:
        return reverse('orders:change-order-status', kwargs={'order_id': str(order_id)})

    def check_order_in_order_data(self, order_data: dict[str, Any], order: Order) -> None:
        self.assertEqual(order_data['user'], order.user.email)
        self.assertEqual(order_data['phone'], order.phone)
        self.assertEqual(order_data['address'], order.address)
        self.assertEqual(order_data['city'], order.city)
        expected_coupon = order.coupon.code if order.coupon else None
        self.assertEqual(order_data['coupon'], expected_coupon)
        self.assertEqual(Decimal(order_data['total_price']), Decimal(order.total_price))
        self.assertEqual(order_data['status'], order.status)
        self.assertEqual(Decimal(order_data['total_price_before_discount']), Decimal(order.total_price_before_discount))
        self.assertEqual(Decimal(order_data['discount_price']), Decimal(order.discount_price))
        self.assertEqual(Decimal(order_data['total_price_after_discount']), Decimal(order.total_price_after_discount))

    def check_contains_order_in_order_response(self, order_response: Response, order: Order) -> bool:
        for order_item in order_response.data:
            if order_item['order_id'] == str(order.order_id):
                self.check_order_in_order_data(order_data=order_item, order=order)
                return True
        return False

    def create_order_data(self, **new_data: Any) -> dict[str, Any]:
        data = {
            'full_name': 'Ivan Petrov',
            'phone': '+78005553535',
            'address': 'Pushkina 14',
            'city': 'Moscow',
        }
        data.update(new_data)
        return data

    def test_anon_user_cannot_get_orders_list(self) -> None:
        # Неправильное получение списка заказов и проверка
        invalid_anon_response = self.anon_client.get(self.orders_list_url)
        self.assertEqual(invalid_anon_response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_normal_user_can_get_his_own_orders_in_orders_list(self) -> None:
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

        # Проверка количества заказов
        self.assertEqual(len(list_normal_response.data), 1)
    
    def test_normal_user_cannot_get_other_orders_in_orders_list(self) -> None:
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

    def _check_admin_or_manger_user_can_get_all_orders(self, client: APIClient) -> None:
        # Получение списка заказов и проверка
        all_orders_response = client.get(self.orders_list_url)
        self.assertEqual(all_orders_response.status_code, status.HTTP_200_OK)

        # Проверка на наличие всехх заказов в списке
        self.assertTrue(
            self.check_contains_order_in_order_response(
                order_response=all_orders_response,
                order=self.order_normal,
            )
        )
        self.assertTrue(
            self.check_contains_order_in_order_response(
                order_response=all_orders_response,
                order=self.order_admin,
            )
        )

        # Проверка количества заказов
        self.assertEqual(len(all_orders_response.data), 2)

    def test_admin_user_can_get_all_orders(self) -> None:
        self._check_admin_or_manger_user_can_get_all_orders(self.admin_client)
    
    def test_manager_user_can_get_all_orders(self) -> None:
        self._check_admin_or_manger_user_can_get_all_orders(self.manager_client)

    def test_anon_user_cannot_get_order_detail(self) -> None:
        # Неправильное получение заказа и проверка
        invalid_anon_response = self.anon_client.get(
            self.get_order_detail_url_with_order_id(order_id=self.order_normal.order_id),
        )
        self.assertEqual(invalid_anon_response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_normal_user_can_get_his_own_order_detail(self) -> None:
        # Получение своего заказа и проверка
        detail_normal_response = self.normal_client.get(
            self.get_order_detail_url_with_order_id(order_id=self.order_normal.order_id),
        )
        self.assertEqual(detail_normal_response.status_code, status.HTTP_200_OK)

        # Проверка на совпадение заказа из ответа
        self.check_order_in_order_data(
            order_data=detail_normal_response.data, order=self.order_normal,
        )
    
    def test_normal_user_cannot_get_other_order_detail(self) -> None:
        # Неправильное получение чужого заказа и проверка
        invalid_normal_response = self.normal_client.get(
            self.get_order_detail_url_with_order_id(order_id=self.order_admin.order_id),
        )
        self.assertEqual(invalid_normal_response.status_code, status.HTTP_404_NOT_FOUND)

    def _check_admin_or_manager_user_can_get_other_order_detail(self, client: APIClient) -> None:
        # Получение своего заказа и проверка
        detail_response = client.get(
            self.get_order_detail_url_with_order_id(order_id=self.order_normal.order_id),
        )
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)

        # Проверка на совпадение заказа из ответа
        self.check_order_in_order_data(
            order_data=detail_response.data, order=self.order_normal,
        )

    def test_admin_user_can_get_other_order_detail(self) -> None:
        self._check_admin_or_manager_user_can_get_other_order_detail(self.admin_client)
    
    def test_manager_user_can_get_other_order_detail(self) -> None:
        self._check_admin_or_manager_user_can_get_other_order_detail(self.manager_client)

    def test_anon_user_cannot_create_order(self) -> None:
        # Данные для создания заказа
        order_data = self.create_order_data()

        # Неправильное создание заказа и проверка
        invalid_anon_response = self.anon_client.post(
            self.orders_list_url, data=order_data,
        )
        self.assertEqual(invalid_anon_response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch('django_prod_shop.orders.api.serializers.send_order_email.delay')
    def test_normal_user_can_create_order(self, mocked_delay: MagicMock) -> None:
        # Данные для создания заказа
        order_data = self.create_order_data()

        # Цена в корзине
        cart_total_price = self.cart_normal.total_price

        # Создание заказа из корзины без отправления письма и проверка
        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            create_normal_response = self.normal_client.post(
                self.orders_list_url, data=order_data,
            )
            self.assertEqual(len(callbacks), 1)
        self.assertEqual(create_normal_response.status_code, status.HTTP_201_CREATED)

        # Проверка на совпадение созданного заказа
        data = create_normal_response.data
        self.assertTrue(Order.objects.filter(order_id=data['order_id']).exists())

        order = Order.objects.get(order_id=data['order_id'])
        self.assertEqual(order.full_name, data['full_name'])
        self.assertEqual(order.phone, data['phone'])
        self.assertEqual(order.address, data['address'])
        self.assertEqual(order.city, data['city'])
        self.assertEqual(order.total_price, cart_total_price)
        self.assertEqual(data['status'], StatusChoices.PENDING)
        self.assertEqual(
            Decimal(order.total_price_before_discount), 
            Decimal(data['total_price_before_discount']),
        )
        self.assertEqual(
            Decimal(order.discount_price), Decimal(data['discount_price'])
        )
        self.assertEqual(
            Decimal(order.total_price_after_discount), 
            Decimal(data['total_price_after_discount']),
        )

        mocked_delay.assert_called_once_with(str(order.order_id))
        self.assertFalse(Cart.objects.filter(user=self.normal_user).exists())
        
    def test_cannot_create_order_without_cart(self) -> None:
        # Данные для создания заказа
        order_data = self.create_order_data()

        # Неправльное создание заказа (без корзины) и проверка
        invalid_order_user_response = self.invalid_order_client.post(
            self.orders_list_url, data=order_data,
        )
        self.assertEqual(
            invalid_order_user_response.status_code, status.HTTP_400_BAD_REQUEST
        )
    
    def test_cannot_create_order_with_empty_cart(self) -> None:
        # Данные для создания заказа
        order_data = self.create_order_data()

        # Создание пустой корзины
        Cart.objects.create(user=self.invalid_order_user)

        # Неправльное создание заказа (с пустой корзиной) и проверка
        invalid_order_user_response = self.invalid_order_client.post(
            self.orders_list_url, data=order_data,
        )
        self.assertEqual(
            invalid_order_user_response.status_code, status.HTTP_400_BAD_REQUEST
        )
    
    def test_cannot_create_order_with_inactive_product(self) -> None:
        # Данные для создания заказа
        order_data = self.create_order_data()

        # Создание корзины с неактивным товаром
        cart = Cart.objects.create(user=self.invalid_order_user)
        CartItem.objects.create(
            cart=cart, product=self.product_inactive, quantity=1
        )

        # Неправльное создание заказа (с неактивным товаром в корзине) и проверка
        invalid_order_user_response = self.invalid_order_client.post(
            self.orders_list_url, data=order_data,
        )
        self.assertEqual(
            invalid_order_user_response.status_code, status.HTTP_400_BAD_REQUEST
        )
    
    def test_cannot_create_order_with_over_product_quantity(self) -> None:
        # Данные для создания заказа
        order_data = self.create_order_data()

        # Создание корзины со слишком большим количеством товара
        cart = Cart.objects.create(user=self.invalid_order_user)
        CartItem.objects.create(
            cart=cart, product=self.product1, quantity=999999
        )

        # Неправльное создание заказа (со слишком большим количеством товара корзине)
        # и проверка
        invalid_order_user_response = self.invalid_order_client.post(
            self.orders_list_url, data=order_data,
        )
        self.assertEqual(
            invalid_order_user_response.status_code, status.HTTP_400_BAD_REQUEST
        )

    def test_items_contains_in_order_response(self) -> None:
        # Получение своего заказа и проверка
        detail_admin_response = self.admin_client.get(
            self.get_order_detail_url_with_order_id(order_id=self.order_admin.order_id),
        )
        self.assertEqual(detail_admin_response.status_code, status.HTTP_200_OK)
        
        # Проверка на вхождение товаров в список заказ
        product_slugs = {item['product_slug'] for item in detail_admin_response.data['items']}
        for order_item in self.order_admin.items.all():
            self.assertIn(order_item.product.slug, product_slugs)
        
        # Проверка вложенных данных
        for item_data in detail_admin_response.data['items']:
            order_item = self.order_admin.items.get(
                product__slug=item_data['product_slug']
            )

            self.assertEqual(item_data['product_title'], order_item.product.title)
            self.assertEqual(Decimal(item_data['price']), order_item.price)
            self.assertEqual(item_data['quantity'], order_item.quantity)
            self.assertEqual(Decimal(item_data['cost']), order_item.cost)

    def test_anon_user_cannot_change_order_status(self) -> None:
        # Неправильная смена статуса и проверка
        invalid_anon_response = self.anon_client.post(
            self.get_order_status_change_url_with_order_id(
                order_id=self.order_normal.order_id, 
            ), data={'status': 'delivered'},
        )
        self.assertEqual(invalid_anon_response.status_code, status.HTTP_401_UNAUTHORIZED)

        # Проверка на необновленность статуса
        self.order_normal.refresh_from_db()
        self.assertFalse(Order.objects.filter(
            order_id=self.order_normal.order_id, status='delivered',
        ).exists())

    def test_normal_user_cannot_change_order_status(self) -> None:
        # Неправильная смена статуса и проверка
        invalid_normal_response = self.normal_client.post(
            self.get_order_status_change_url_with_order_id(
                order_id=self.order_normal.order_id, 
            ), data={'status': 'delivered'},
        )
        self.assertEqual(invalid_normal_response.status_code, status.HTTP_403_FORBIDDEN)

        # Проверка на необновленность статуса
        self.order_normal.refresh_from_db()
        self.assertNotEqual(self.order_normal.status, 'delivered')

    def test_admin_user_cannot_set_invalid_status(self) -> None:
        # Неправильная смена статуса и проверка
        invalid_admin_response = self.admin_client.post(
            self.get_order_status_change_url_with_order_id(
                order_id=self.order_normal.order_id, 
            ), data={'status': 'invalid_status'},
        )
        self.assertEqual(invalid_admin_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(invalid_admin_response.data['status'], 'Такого статуса не существует')

    def _check_admin_or_manager_user_can_change_any_order_status(self, client: APIClient) -> None:
        # Смена статуса и проверка
        change_status_response = client.post(
            self.get_order_status_change_url_with_order_id(
                order_id=self.order_normal.order_id, 
            ), data={'status': 'delivered'},
        )
        self.assertEqual(change_status_response.status_code, status.HTTP_200_OK)
        self.assertEqual(change_status_response.data['status'], 'delivered')

        # Проверка на обновленность статуса
        self.order_normal.refresh_from_db()
        self.assertEqual(self.order_normal.status, 'delivered')

    def test_admin_user_can_change_any_order_status(self) -> None:
        self._check_admin_or_manager_user_can_change_any_order_status(self.admin_client)
    def test_manager_user_can_change_any_order_status(self) -> None:
        self._check_admin_or_manager_user_can_change_any_order_status(self.manager_client)
