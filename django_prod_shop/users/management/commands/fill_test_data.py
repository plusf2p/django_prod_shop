from decimal import Decimal
from datetime import timedelta
import uuid

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from django_prod_shop.users.models import Profile
from django_prod_shop.products.models import Category, Product
from django_prod_shop.coupons.models import Coupon
from django_prod_shop.cart.models import Cart, CartItem
from django_prod_shop.orders.models import Order, OrderItem, StatusChoices as OrderStatusChoices
from django_prod_shop.payment.models import Payment, StatusChoices as PaymentStatusChoices


class Command(BaseCommand):
    help = 'Заполнение Б/Д тестовыми данными'

    TEST_USERS_EMAILS = [
        'first_normal_user@mail.ru',
        'second_normal_user@mail.ru',
        'manager_user@mail.ru',
        'admin_user@mail.ru',
    ]

    TEST_CATEGORIES_SLUGS = [
        'smartfony',
        'noutbuki',
        'aksessuary',
    ]

    TEST_PRODUCTS_SLUGS = [
        'iphone-15',
        'samsung-galaxy-s24',
        'macbook-air-m3',
        'lenovo-ideapad-5',
        'besprovodnye-naushniki',
        'besprovodnaya-mysh',
    ]

    TEST_COUPONS_CODES = [
        'test-coupon-1',
        'test-coupon-2',
    ]

    TEST_ORDERS_IDS = [
        uuid.UUID('11111111-AAAA-1111-AAAA-111111111111'),
        uuid.UUID('22222222-BBBB-2222-BBBB-222222222222'),
        uuid.UUID('33333333-CCCC-3333-CCCC-333333333333'),
    ]

    TEST_PAYMENTS_IDS = [
        uuid.UUID('AAAAAAAA-1111-AAAA-1111-AAAAAAAAAAAA'),
        uuid.UUID('BBBBBBBB-2222-BBBB-2222-BBBBBBBBBBBB'),
        uuid.UUID('CCCCCCCC-3333-CCCC-3333-CCCCCCCCCCCC'),
    ]


    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Удалить тестовые данные перед заполнением'
        )

    @transaction.atomic
    def handle(self, *args, **options):
        user_model = get_user_model()

        if options['clear']:
            self._clear_test_data(user_model)
        
        users = self._create_users(user_model)
        self._add_groups(users)
        self._fill_profiles(users)

        categories = self._create_categories()

        products = self._create_products(categories)

        coupons = self._create_coupons()

        carts = self._create_carts(users, coupons)
        self._create_cart_items(products, carts)

        orders = self._create_orders(carts)
        self._create_order_items(carts, orders)

        self._create_payments(orders)

        self.stdout.write(self.style.SUCCESS('Тестовые данные успешно заполнены'))

    def _clear_test_data(self, user_model):
        self.stdout.write(self.style.WARNING('Удаление тестовых данных...'))

        Payment.objects.filter(payment_id__in=self.TEST_PAYMENTS_IDS).delete()

        Order.objects.filter(order_id__in=self.TEST_ORDERS_IDS).delete()

        Cart.objects.filter(user__email__in=self.TEST_USERS_EMAILS).delete()

        Coupon.objects.filter(code__in=self.TEST_COUPONS_CODES).delete()

        Product.objects.filter(slug__in=self.TEST_PRODUCTS_SLUGS).delete()

        Category.objects.filter(slug__in=self.TEST_CATEGORIES_SLUGS).delete()

        user_model.objects.filter(email__in=self.TEST_USERS_EMAILS).delete()

    def _create_users(self, user_model):
        users_data = {
            'first': {
                'email': 'first_normal_user@mail.ru',
                'password': 'first_normal_user_123',
                'is_staff': False,
                'is_superuser': False,
            },
            'second': {
                'email': 'second_normal_user@mail.ru',
                'password': 'second_normal_user_123',
                'is_staff': False,
                'is_superuser': False,
            },
            'manager': {
                'email': 'manager_user@mail.ru',
                'password': 'manager_user_123',
                'is_staff': True,
                'is_superuser': False,
            },
            'admin': {
                'email': 'admin_user@mail.ru',
                'password': 'admin_user_123',
                'is_staff': True,
                'is_superuser': False,
            },
        }

        users = {}

        for key, data in users_data.items():
            user, created = user_model.objects.get_or_create(
                email=data['email'],
                defaults={
                    'is_staff': data['is_staff'],
                    'is_superuser': data['is_superuser'],
                }
            )

            if not created:
                user.is_staff = data['is_staff']
                user.is_superuser = data['is_superuser']
            user.set_password(data['password'])
            user.save()

            users[key] = user
        
        self.stdout.write(self.style.SUCCESS('Тестовые пользователи созданы/обновлены'))

        return users

    def _add_groups(self, users):
        try:
            manager_group = Group.objects.get(name='Manager')
            admin_group = Group.objects.get(name='Admin')
        except Group.DoesNotExist:
            raise CommandError('Ошибка при получении ролей. Введите команду для создания ролей или проверьте группы')

        users['manager'].groups.add(manager_group)
        users['admin'].groups.add(admin_group)

        self.stdout.write(self.style.SUCCESS('Роли тестовых пользователей назначены'))

    def _fill_profiles(self, users):
        profiles_data = {
            'first': {
                'full_name': 'Иван Петров',
                'phone': '+78005553535',
                'city': 'Moscow',
                'address': 'Pushkina 15',
            },
            'second': {
                'full_name': 'Петр Иванов',
                'phone': '+1315315500',
                'city': 'Sterlitamak',
                'address': 'Gagarina 15',
            },
            'manager': {
                'full_name': 'Менеджер',
                'phone': '+79905553995',
                'city': 'Kazan',
                'address': 'Lenina 22',
            },
            'admin': {
                'full_name': 'Админ',
                'phone': '+79005553636',
                'city': 'Moscow',
                'address': 'Pushkina 19',
            },
        }

        for key, data in profiles_data.items():
            user = users[key]
            
            try:
                profile = user.profile
            except Profile.DoesNotExist:
                raise CommandError('Ошибка при получении профиля. Проверьте сигналы и модели')

            profile.full_name = data['full_name']
            profile.phone = data['phone']
            profile.city = data['city']
            profile.address = data['address']
            profile.save()
        
        self.stdout.write(self.style.SUCCESS('Тестовые профили заполнены/обновлены'))

    def _create_categories(self):
        categories_data = [
            {
                'title': 'Смартфоны',
                'slug': 'smartfony',
                'description': 'Современные смартфоны разных брендов.',
            },
            {
                'title': 'Ноутбуки',
                'slug': 'noutbuki',
                'description': 'Ноутбуки для работы, учёбы и игр.',
            },
            {
                'title': 'Аксессуары',
                'slug': 'aksessuary',
                'description': 'Полезные аксессуары для техники.',
            },
        ]

        categories = {}

        for data in categories_data:
            category, _ = Category.objects.update_or_create(
                slug=data['slug'],
                defaults={
                    'title': data['title'],
                    'description': data['description'],
                }
            )
            categories[data['slug']] = category

        self.stdout.write(self.style.SUCCESS('Тестовые категории созданы/обновлены'))

        return categories

    def _create_products(self, categories):
        products_data = [
            {
                'title': 'iPhone 15',
                'slug': 'iphone-15',
                'category_slug': 'smartfony',
                'quantity': 15,
                'reserved_quantity': 2,
                'description': 'Смартфон Apple нового поколения.',
                'price': Decimal('99990.00'),
                'is_active': True,
            },
            {
                'title': 'Samsung Galaxy S24',
                'slug': 'samsung-galaxy-s24',
                'category_slug': 'smartfony',
                'quantity': 20,
                'reserved_quantity': 3,
                'description': 'Флагманский смартфон Samsung.',
                'price': Decimal('89990.00'),
                'is_active': True,
            },
            {
                'title': 'MacBook Air M3',
                'slug': 'macbook-air-m3',
                'category_slug': 'noutbuki',
                'quantity': 8,
                'reserved_quantity': 1,
                'description': 'Лёгкий и производительный ноутбук Apple.',
                'price': Decimal('149990.00'),
                'is_active': True,
            },
            {
                'title': 'Lenovo IdeaPad 5',
                'slug': 'lenovo-ideapad-5',
                'category_slug': 'noutbuki',
                'quantity': 12,
                'reserved_quantity': 2,
                'description': 'Универсальный ноутбук для работы и дома.',
                'price': Decimal('65990.00'),
                'is_active': True,
            },
            {
                'title': 'Беспроводные наушники',
                'slug': 'besprovodnye-naushniki',
                'category_slug': 'aksessuary',
                'quantity': 25,
                'reserved_quantity': 5,
                'description': 'Удобные Bluetooth-наушники.',
                'price': Decimal('7990.00'),
                'is_active': True,
            },
            {
                'title': 'Беспроводная мышь',
                'slug': 'besprovodnaya-mysh',
                'category_slug': 'aksessuary',
                'quantity': 18,
                'reserved_quantity': 2,
                'description': 'Компактная мышь для ноутбука и ПК.',
                'price': Decimal('2490.00'),
                'is_active': True,
            },
        ]

        products = {}

        for data in products_data:
            product, _ = Product.objects.update_or_create(
                slug=data['slug'],
                defaults={
                    'title': data['title'],
                    'category': categories[data['category_slug']],
                    'quantity': data['quantity'],
                    'reserved_quantity': data['reserved_quantity'],
                    'description': data['description'],
                    'price': data['price'],
                    'is_active': data['is_active'],
                }
            )

            products[data['slug']] = product
        
        self.stdout.write(self.style.SUCCESS('Тестовые товары созданы/обновлены'))

        return products

    def _create_coupons(self):
        valid_from = timezone.now().date()
        valid_to = (timezone.now() + timedelta(days=7)).date()

        coupons_data = [
            {
                'code': 'test-coupon-1',
                'valid_from': valid_from,
                'valid_to': valid_to,
                'discount': 25,
            },
            {
                'code': 'test-coupon-2',
                'valid_from': valid_from,
                'valid_to': valid_to,
                'discount': 50,
            },
        ]

        coupons = {}

        for data in coupons_data:
            coupon, _ = Coupon.objects.update_or_create(
                code=data['code'],
                defaults={
                    'valid_from': data['valid_from'],
                    'valid_to': data['valid_to'],
                    'discount': data['discount'],
                }
            )

            coupons[data['code']] = coupon

        self.stdout.write(self.style.SUCCESS('Тестовые купоны созданы/обновлены'))

        return coupons

    def _create_carts(self, users, coupons):
        carts_data = {
            'first': {
                'user': users['first'],
                'coupon': None,
            },
            'second': {
                'user': users['second'],
                'coupon': coupons['test-coupon-1'],
            },
            'manager': {
                'user': users['manager'],
                'coupon': coupons['test-coupon-2'],
            },
        }

        carts = {}

        for key, data in carts_data.items():
            cart, _ = Cart.objects.update_or_create(
                user=data['user'],
                defaults={
                    'coupon': data['coupon']
                }
            )

            carts[key] = cart
        
        self.stdout.write(self.style.SUCCESS('Тестовые корзины созданы/обновлены'))

        return carts

    def _create_cart_items(self, products, carts):
        cart_items_data = [
            {
                'cart_key': 'first',
                'product_slug': 'iphone-15',
                'quantity': 1,
            },
            {
                'cart_key': 'first',
                'product_slug': 'samsung-galaxy-s24',
                'quantity': 2,
            },
            {
                'cart_key': 'second',
                'product_slug': 'macbook-air-m3',
                'quantity': 3,
            },
            {
                'cart_key': 'second',
                'product_slug': 'lenovo-ideapad-5',
                'quantity': 1,
            },
            {
                'cart_key': 'manager',
                'product_slug': 'besprovodnye-naushniki',
                'quantity': 2,
            },
            {
                'cart_key': 'manager',
                'product_slug': 'besprovodnaya-mysh',
                'quantity': 3,
            },
        ]
        for data in cart_items_data:
            CartItem.objects.update_or_create(
                cart=carts[data['cart_key']],
                product=products[data['product_slug']],
                defaults={
                    'quantity': data['quantity'],
                }
            )
        
        self.stdout.write(self.style.SUCCESS('Тестовые товары корзины созданы/обновлены'))

    def _create_orders(self, carts):
        orders_ids = {
            'first': self.TEST_ORDERS_IDS[0],
            'second': self.TEST_ORDERS_IDS[1],
            'manager': self.TEST_ORDERS_IDS[2],
        }

        orders_statuses = {
            'first': OrderStatusChoices.PAID,
            'second': OrderStatusChoices.DELIVERED,
            'manager': OrderStatusChoices.CANCELLED,
        }

        orders = {}

        for key, cart in carts.items():
            profile = cart.user.profile

            order, _ = Order.objects.update_or_create(
                order_id=orders_ids[key],
                defaults={
                    'user': cart.user,
                    'full_name': profile.full_name,
                    'phone': profile.phone,
                    'address': profile.address,
                    'city': profile.city,
                    'coupon': cart.coupon,
                    'total_price': cart.total_price,
                    'status': orders_statuses[key],
                }
            )

            orders[key] = order

        self.stdout.write(self.style.SUCCESS('Тестовые заказы созданы/обновлены'))
        
        return orders

    def _create_order_items(self, carts, orders):
        for key, cart in carts.items():
            order = orders[key]

            for cart_item in cart.cart_items.select_related('product'):
                OrderItem.objects.update_or_create(
                    order=order,
                    product=cart_item.product,
                    defaults={
                        'price': cart_item.product.price,
                        'quantity': cart_item.quantity,
                    }
                )
        
        self.stdout.write(self.style.SUCCESS('Тестовые товары заказов созданы/обновлены'))

    def _create_payments(self, orders):
        payments_ids = {
            'first': self.TEST_PAYMENTS_IDS[0],
            'second': self.TEST_PAYMENTS_IDS[1],
            'manager': self.TEST_PAYMENTS_IDS[2],
        }

        payments_statuses = {
            'first': PaymentStatusChoices.PENDING,
            'second': PaymentStatusChoices.PAID,
            'manager': PaymentStatusChoices.CANCELLED,
        }
       
        for key, order in orders.items():
            Payment.objects.update_or_create(
                payment_id=payments_ids[key],
                defaults={
                    'order': order,
                    'amount': order.total_price_after_discount,
                    'status': payments_statuses[key],
                }
            )
