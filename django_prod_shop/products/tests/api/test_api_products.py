from decimal import Decimal
from typing import Any
from uuid import uuid4

from django.core.management import call_command
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.cache import cache
from django.urls import reverse

from rest_framework.test import APITestCase, APIClient
from rest_framework.response import Response
from rest_framework import status

from django_prod_shop.products.models import Category, Product


user_model = get_user_model()


class ProductAPITest(APITestCase):
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
        cls.product_list_url = reverse('products:product-list')

        ### Products ###

        # Создание стартовой категории
        cls.category = Category.objects.create(
            title='Test category', description='test description', slug='test-category'
        )
        
        # Создание двух стартовых товаров
        cls.product1 = Product.objects.create(
            title='Test title of first product', category=cls.category, quantity=10, reserved_quantity=5, 
            description='1', slug='test-title-of-first-product', price=400, is_active=True,
        )
        cls.product2 = Product.objects.create(
            title='Test title of second product', category=cls.category, quantity=100, reserved_quantity=10, 
            description='2', slug='test-title-of-second-product', price=200, is_active=True,
        )

    def setUp(self) -> None:
        cache.clear()
        self.admin_client = APIClient()
        self.normal_client = APIClient()
        self.manager_client = APIClient()
        self.anon_client = APIClient()

        # Авторизация админа и обычного пользователя
        self.normal_client.force_authenticate(user=self.normal_user)
        self.manager_client.force_authenticate(user=self.manager_user)
        self.admin_client.force_authenticate(user=self.admin_user)
    
    def get_product_detail_url_with_slug(self, slug: str) -> str:
        return reverse('products:product-detail', kwargs={'slug': slug})

    def get_list_items(self, products_response: Response) -> dict[str, Any]:
        if 'results' in products_response.data:
            return products_response.data['results']
        return products_response.data

    def get_list_of_slugs(self, products_response: Response) -> set[str]:
        # Получение множества из слагов для избежания повторений
        return {item['slug'] for item in self.get_list_items(products_response)}

    def get_item_in_list(self, products_response: Response, slug: str) -> dict[str, Any]:
        # Проверка на наличие товара в ответе
        for item in self.get_list_items(products_response):
            if item['slug'] == slug:
                return item
        self.fail(f"Товара со слагом '{slug}' не найдено")

    def update_product_data(self, **new_data: dict[str, Any]) -> dict[str, Any]:
        data = {
            'title': 'Test new title',
            'category_id': self.category.pk,
            'quantity': 100,
            'reserved_quantity': 15,
            'description': 'Test new description',
            'slug': f'test-new-title-{uuid4().hex[:8]}',
            'price': 9999,
            'is_active': True,
        }
        data.update(new_data)
        return data

    def check_contains_product_in_product_data(
            self, product_data: dict[str, Any], product: Product,
        ) -> None:
        self.assertEqual(product_data['title'], product.title)
        self.assertEqual(Decimal(product_data['price']), Decimal(product.price))
        self.assertEqual(product_data['category_name'], product.category.title)
        self.assertEqual(product_data['quantity'], product.quantity)
        self.assertEqual(product_data['reserved_quantity'], product.reserved_quantity)

    def check_product_from_db(self, slug: str, **data: dict[str, Any]) -> Product:
        # Проверка товара на создание в бд
        self.assertTrue(Product.objects.filter(slug=slug).exists())
        product = Product.objects.get(slug=slug)
        self.assertEqual(product.slug, slug)

        for key, value in data.items():
            if key == 'price':
                self.assertEqual(Decimal(getattr(product, key)), Decimal(value))
            else:
                self.assertEqual(getattr(product, key), value)
        
        return product

    def test_anon_user_can_order_products(self) -> None:
        # Создание нового товара
        new_product = Product.objects.create(**self.update_product_data())

        # Получение списка товаров и проверка
        ordering_response = self.anon_client.get(self.product_list_url)
        self.assertEqual(ordering_response.status_code, status.HTTP_200_OK)

        # Получение товара из списка и проверка
        product_list = self.get_list_items(ordering_response)
        self.assertEqual(product_list[0]['slug'], new_product.slug)

    def test_anon_user_can_search_products_by_category_title(self) -> None:
        # Получение второго товара по поиску по полю title и проверка
        searched_response = self.anon_client.get(f'{self.product_list_url}?search={self.category.title}')
        self.assertEqual(searched_response.status_code, status.HTTP_200_OK)
        
        # Получение слагов в ответе и проверка на совпадение и несовпадение товаров
        all_products_slugs = self.get_list_of_slugs(searched_response)
        self.assertIn(self.product1.slug, all_products_slugs)
        self.assertIn(self.product2.slug, all_products_slugs)

    def test_anon_user_can_search_products_by_product_title(self) -> None:
        # Получение второго товара по поиску по полю title и проверка
        searched_response = self.anon_client.get(f'{self.product_list_url}?search=second')
        self.assertEqual(searched_response.status_code, status.HTTP_200_OK)
        
        # Получение слагов в ответе и проверка на совпадение и несовпадение товаров
        all_products_slugs = self.get_list_of_slugs(searched_response)
        self.assertIn(self.product2.slug, all_products_slugs)
        self.assertNotIn(self.product1.slug, all_products_slugs)

        # Получение первого товара по поиску по полю title и проверка
        searched_response = self.anon_client.get(f'{self.product_list_url}?search=first')
        self.assertEqual(searched_response.status_code, status.HTTP_200_OK)
        
        # Получение слагов в ответе и проверка на совпадение и несовпадение товаров
        all_products_slugs = self.get_list_of_slugs(searched_response)
        self.assertIn(self.product1.slug, all_products_slugs)
        self.assertNotIn(self.product2.slug, all_products_slugs)

    def test_anon_user_can_filter_products(self) -> None:
        # Получение второго товара по фильтру по полю price и проверка
        filtered_response = self.anon_client.get(f'{self.product_list_url}?price_min=300')
        self.assertEqual(filtered_response.status_code, status.HTTP_200_OK)
        
        # Получение слагов в ответе и проверка на совпадение и несовпадение товаров
        all_products_slugs = self.get_list_of_slugs(filtered_response)
        self.assertIn(self.product1.slug, all_products_slugs)
        self.assertNotIn(self.product2.slug, all_products_slugs)

        # Получение второго товара по фильтру по полю slug
        filtered_response = self.anon_client.get(f'{self.product_list_url}?slug=test-title-of-second-product')
        self.assertEqual(filtered_response.status_code, status.HTTP_200_OK)
        
        # Получение слагов в ответе и проверка на совпадение и несовпадение товаров и проверка
        all_products_slugs = self.get_list_of_slugs(filtered_response)
        self.assertIn(self.product2.slug, all_products_slugs)
        self.assertNotIn(self.product1.slug, all_products_slugs)

        # Получение обоих товаров по фильтру по полю title
        filtered_response = self.anon_client.get(f'{self.product_list_url}?title=test')
        self.assertEqual(filtered_response.status_code, status.HTTP_200_OK)
        
        # Получение слагов в ответе и проверка на совпадение обоих товаров и проверка
        all_products_slugs = self.get_list_of_slugs(filtered_response)
        self.assertIn(self.product1.slug, all_products_slugs)
        self.assertIn(self.product2.slug, all_products_slugs)
    
    def test_anon_user_can_get_product_list(self) -> None:
        # Получение всех товаров и проверка
        list_response = self.anon_client.get(self.product_list_url)
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)

        # Получение и проверка первого товара
        product1_data = self.get_item_in_list(products_response=list_response, slug=self.product1.slug)
        self.check_contains_product_in_product_data(product_data=product1_data, product=self.product1)

        # Получение и проверка второго товара
        product2_data = self.get_item_in_list(products_response=list_response, slug=self.product2.slug)
        self.check_contains_product_in_product_data(product_data=product2_data, product=self.product2)
    
    def test_anon_user_can_get_product_detail(self) -> None:
        # Взятие товара и проверка
        detail_response = self.anon_client.get(
            self.get_product_detail_url_with_slug(self.product1.slug)
        )
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)

        # Проверка товара
        self.check_contains_product_in_product_data(
            product_data=detail_response.data, product=self.product1,
        )

        self.assertIn('reviews', detail_response.data)
        self.assertIn('similar_products', detail_response.data)

    def test_anon_user_cannot_get_product_detail_with_invalid_data(self) -> None:
        # Неправильное взятие товара и проверка
        wrong_detail_response = self.anon_client.get(
            self.get_product_detail_url_with_slug('wrong-slug')
        )
        self.assertEqual(wrong_detail_response.status_code, status.HTTP_404_NOT_FOUND)

    def test_anon_user_cannot_create_product(self) -> None:
        # Данные для создания товара
        product_data = self.update_product_data()

        # Неправильная попытка создать товар анонимно
        wrong_anon_response = self.anon_client.post(
            self.product_list_url, data=product_data, format='multipart',
        )
        self.assertEqual(wrong_anon_response.status_code, status.HTTP_401_UNAUTHORIZED)

        # Проверка на неcоздание товара
        self.assertFalse(Product.objects.filter(slug=product_data['slug']).exists())

    def test_normal_user_cannot_create_product(self) -> None:
        # Данные для создания товара
        product_data = self.update_product_data()

        # Неправильная попытка создать товар обычному пользователю
        wrong_normal_response = self.normal_client.post(
            self.product_list_url, data=product_data, format='multipart',
        )
        self.assertEqual(wrong_normal_response.status_code, status.HTTP_403_FORBIDDEN)

        # Проверка на неcоздание товара
        self.assertFalse(Product.objects.filter(slug=product_data['slug']).exists())

    def test_admin_user_cannot_create_product_with_invalid_data(self) -> None:
        # Неправильные данные для создания товара
        wrong_product_data = {
            'title': 'Wrong title',
            'description': 'Wrong description',
            'slug': 'wrong-title',
        }

        # Неправильная попытка создать товар админом и проверка
        wrong_response = self.admin_client.post(
            self.product_list_url, data=wrong_product_data, format='multipart',
        )
        self.assertEqual(wrong_response.status_code, status.HTTP_400_BAD_REQUEST)

        # Проверка на неcоздание товара
        self.assertFalse(Product.objects.filter(slug=wrong_product_data['slug']).exists())

        # Взятие несуществующего товара после попытки создания и проверка
        wrong_product_detail_response = self.normal_client.get(
            self.get_product_detail_url_with_slug(wrong_product_data['slug'])
        )
        self.assertEqual(wrong_product_detail_response.status_code, status.HTTP_404_NOT_FOUND)

    def test_admin_user_cannot_create_product_with_price_lt_0(self) -> None:
        # Неправильные данные для создания товара
        wrong_product_data = self.update_product_data(price=Decimal('-999'))

        # Неправильная попытка создать товар админом и проверка
        wrong_response = self.admin_client.post(
            self.product_list_url, data=wrong_product_data, format='multipart',
        )
        self.assertEqual(wrong_response.status_code, status.HTTP_400_BAD_REQUEST)

        # Проверка на неcоздание товара
        self.assertFalse(Product.objects.filter(slug=wrong_product_data['slug']).exists())
    
    def test_admin_user_cannot_create_product_with_quantity_lt_reserved_quantity(self) -> None:
        # Неправильные данные для создания товара
        wrong_product_data = self.update_product_data(quantity=10, reserved_quantity=20)

        # Неправильная попытка создать товар админом и проверка
        wrong_response = self.admin_client.post(
            self.product_list_url, data=wrong_product_data, format='multipart',
        )
        self.assertEqual(wrong_response.status_code, status.HTTP_400_BAD_REQUEST)

        # Проверка на неcоздание товара
        self.assertFalse(Product.objects.filter(slug=wrong_product_data['slug']).exists())

    def test_admin_user_can_create_product(self) -> None:
        # Данные для создания товара
        product_data = self.update_product_data()

        # Создание товара админом и проверка
        new_created_product_response = self.admin_client.post(
            self.product_list_url, data=product_data, format='multipart',
        )
        self.assertEqual(new_created_product_response.status_code, status.HTTP_201_CREATED)

        # Проверка созданного товара
        self.assertEqual(
            new_created_product_response.data['title'], product_data['title']
        )
        self.assertEqual(
            Decimal(new_created_product_response.data['price']), Decimal(product_data['price'])
        )
        self.assertEqual(
            new_created_product_response.data['slug'], product_data['slug']
        )
        self.assertEqual(
            new_created_product_response.data['quantity'], product_data['quantity']
        )
        self.assertEqual(
            new_created_product_response.data['reserved_quantity'], product_data['reserved_quantity']
        )

        # Проверка нового товара
        new_product = self.check_product_from_db(
            slug=product_data['slug'],
            title=product_data['title'],
            price=product_data['price'],
            quantity=product_data['quantity'],
            reserved_quantity=product_data['reserved_quantity'],
            is_active=product_data['is_active'],
        )

        # Получение товара и проверка
        detail_response = self.normal_client.get(
            self.get_product_detail_url_with_slug(new_product.slug)
        )
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)
        self.check_contains_product_in_product_data(detail_response.data, new_product)
    
    def test_manager_user_can_create_product(self) -> None:
        # Данные для создания товара
        product_data = self.update_product_data()

        # Создание товара админом и проверка
        new_created_product_response = self.manager_client.post(
            self.product_list_url, data=product_data, format='multipart',
        )
        self.assertEqual(new_created_product_response.status_code, status.HTTP_201_CREATED)

        # Проверка созданного товара
        self.assertEqual(
            new_created_product_response.data['title'], product_data['title']
        )
        self.assertEqual(
            Decimal(new_created_product_response.data['price']), Decimal(product_data['price'])
        )
        self.assertEqual(
            new_created_product_response.data['slug'], product_data['slug']
        )
        self.assertEqual(
            new_created_product_response.data['quantity'], product_data['quantity']
        )
        self.assertEqual(
            new_created_product_response.data['reserved_quantity'], product_data['reserved_quantity']
        )

        # Проверка нового товара
        new_product = self.check_product_from_db(
            slug=product_data['slug'],
            title=product_data['title'],
            price=product_data['price'],
            quantity=product_data['quantity'],
            reserved_quantity=product_data['reserved_quantity'],
            is_active=product_data['is_active'],
        )

        # Получение товара и проверка
        detail_response = self.manager_client.get(
            self.get_product_detail_url_with_slug(new_product.slug)
        )
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)
        self.check_contains_product_in_product_data(detail_response.data, new_product)

    def test_anon_user_cannot_put_product(self) -> None:
        # Данные для полного обновления товара
        new_product_data = self.update_product_data()

        # Неправильная попытка обновить товар анонимно и проверка
        wrong_anon_response = self.anon_client.put(
            self.get_product_detail_url_with_slug(self.product1.slug), 
            data=new_product_data, format='multipart',
        )
        self.assertEqual(wrong_anon_response.status_code, status.HTTP_401_UNAUTHORIZED)
        
        # Проверка на необновление товара
        self.product1.refresh_from_db()
        self.assertFalse(Product.objects.filter(slug=new_product_data['slug']).exists())

    def test_normal_user_cannot_put_product(self) -> None:
        # Данные для полного обновления товара
        new_product_data = self.update_product_data()

        # Неправильная попытка обновить товар обычному пользователю  и проверка
        wrong_normal_response = self.normal_client.put(
            self.get_product_detail_url_with_slug(self.product1.slug), 
            data=new_product_data, format='multipart',
        )
        self.assertEqual(wrong_normal_response.status_code, status.HTTP_403_FORBIDDEN)

        # Проверка на необновление товара
        self.product1.refresh_from_db()
        self.assertFalse(Product.objects.filter(slug=new_product_data['slug']).exists())

    def test_admin_user_cannot_put_product_with_invalid_data(self) -> None:
        # Неправильные данные для полного обновления
        wrong_product_data = {
            'description': 'Wrong description',
            'slug': 'wrong-slug',
        }

        # Неправильное полное обновление товара админом и проверка
        wrong_response = self.admin_client.put(
            self.get_product_detail_url_with_slug(self.product1.slug), 
            data=wrong_product_data, format='multipart',
        )
        self.assertEqual(wrong_response.status_code, status.HTTP_400_BAD_REQUEST)

        # Проверка на необновление товара
        self.product1.refresh_from_db()
        self.assertFalse(Product.objects.filter(slug=wrong_product_data['slug']).exists())

        # Неправильное взятие товара после неправильного полного обновления
        wrong_response = self.admin_client.get(
            self.get_product_detail_url_with_slug(wrong_product_data['slug']),
        )
        self.assertEqual(wrong_response.status_code, status.HTTP_404_NOT_FOUND)    

    def test_admin_user_can_put_product(self) -> None:
        # Данные для полного обновления товара
        new_product_data = self.update_product_data()

        # Старый слаг
        old_slug = self.product1.slug

        # Полное обновление товара админом и проверка
        put_response = self.admin_client.put(
            self.get_product_detail_url_with_slug(self.product1.slug), 
            data=new_product_data, format='multipart',
        )
        self.assertEqual(put_response.status_code, status.HTTP_200_OK)
        
        # Проверка обновленного товара
        updated_product = self.check_product_from_db(
            slug=new_product_data['slug'],
            title=new_product_data['title'],
            price=new_product_data['price'],
            quantity=new_product_data['quantity'],
            reserved_quantity=new_product_data['reserved_quantity'],
            description=new_product_data['description'],
            is_active=new_product_data['is_active'],
        )
        self.assertNotEqual(updated_product.slug, old_slug)

        # Получение и проверка обновленного товара
        detail_response = self.admin_client.get(
            self.get_product_detail_url_with_slug(new_product_data['slug'])
        )
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)
        self.assertEqual(Decimal(detail_response.data['price']), Decimal(new_product_data['price']))
        self.assertEqual(detail_response.data['quantity'], new_product_data['quantity'])
    
    def test_manager_user_can_put_product(self) -> None:
        # Данные для полного обновления товара
        new_product_data = self.update_product_data()

        # Старый слаг
        old_slug = self.product1.slug

        # Полное обновление товара админом и проверка
        put_response = self.manager_client.put(
            self.get_product_detail_url_with_slug(self.product1.slug), 
            data=new_product_data, format='multipart',
        )
        self.assertEqual(put_response.status_code, status.HTTP_200_OK)
        
        # Проверка обновленного товара
        updated_product = self.check_product_from_db(
            slug=new_product_data['slug'],
            title=new_product_data['title'],
            price=new_product_data['price'],
            quantity=new_product_data['quantity'],
            reserved_quantity=new_product_data['reserved_quantity'],
            description=new_product_data['description'],
            is_active=new_product_data['is_active'],
        )
        self.assertNotEqual(updated_product.slug, old_slug)

        # Получение и проверка обновленного товара
        detail_response = self.manager_client.get(
            self.get_product_detail_url_with_slug(new_product_data['slug'])
        )
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)
        self.assertEqual(Decimal(detail_response.data['price']), Decimal(new_product_data['price']))
        self.assertEqual(detail_response.data['quantity'], new_product_data['quantity'])
    
    def test_anon_user_cannot_patch_product(self) -> None:
        # Данные для частичного обновления товара
        new_product_data = {
            'price': 500,
            'quantity': 400,
        }

        # Неправильное частичное обновление товара анонимным пользователем и проверка
        wrong_anon_response = self.anon_client.patch(
            self.get_product_detail_url_with_slug(self.product1.slug), 
            data=new_product_data, format='multipart',
        )
        self.assertEqual(wrong_anon_response.status_code, status.HTTP_401_UNAUTHORIZED)

        # Проверка на необновление товара в БД
        self.product1.refresh_from_db()
        self.check_product_from_db(
            slug=self.product1.slug, 
            price=self.product1.price, 
            quantity=self.product1.quantity,
        )

    def test_normal_user_cannot_patch_product(self) -> None:
        # Данные для частичного обновления товара
        new_product_data = {
            'price': 500,
            'quantity': 400,
        }

        # Неправильное частичное обновление товара обычным пользователем и проверка
        wrong_normal_response = self.normal_client.patch(
            self.get_product_detail_url_with_slug(self.product1.slug),  
            data=new_product_data, format='multipart',
        )
        self.assertEqual(wrong_normal_response.status_code, status.HTTP_403_FORBIDDEN)

        # Проверка на необновление товара в БД
        self.product1.refresh_from_db()
        self.check_product_from_db(
            slug=self.product1.slug, 
            price=self.product1.price,
            quantity=self.product1.quantity,
        )

    def test_admin_user_cannot_patch_product_with_invalid_data(self) -> None:
        # Неправильные данные для частичного обновления
        wrong_product_data = {
            'title': '',
            'description': 'Wrong description',
            'slug': 'wrong-slug',
        }

        # Неправильное частичное обновление товара и проверка
        wrong_patch_response = self.admin_client.patch(
            self.get_product_detail_url_with_slug(self.product1.slug), 
            data=wrong_product_data, format='multipart',
        )
        self.assertEqual(wrong_patch_response.status_code, status.HTTP_400_BAD_REQUEST)

        # Проверка на необновление товара в БД
        self.product1.refresh_from_db()
        self.assertFalse(Product.objects.filter(slug=wrong_product_data['slug']).exists())

        # Неправильное взятие товара после частичного обновления и проверка
        wrong_response = self.admin_client.get(
            reverse('products:product-detail', kwargs={'slug': wrong_product_data['slug']}),
        )
        self.assertEqual(wrong_response.status_code, status.HTTP_404_NOT_FOUND)

    def test_admin_user_can_patch_product(self) -> None:
        # Данные для частичного обновления товара
        new_product_data = {
            'price': 500,
            'quantity': 400,
        }

        # Частичное обновление товара админом и проверка
        patch_response = self.admin_client.patch(
            self.get_product_detail_url_with_slug(self.product1.slug),
            data=new_product_data, format='multipart',
        )
        self.assertEqual(patch_response.status_code, status.HTTP_200_OK)

        # Проверка на обновление товара в БД
        self.product1.refresh_from_db()
        self.check_product_from_db(
            slug=self.product1.slug,
            price=500,
            quantity=400,
        )

        # Взятие обновленного товара и проверка
        response = self.admin_client.get(
            self.get_product_detail_url_with_slug(self.product1.slug),
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Проверка обновленного товара
        self.assertEqual(Decimal(response.data['price']), Decimal(new_product_data['price']))
        self.assertEqual(response.data['quantity'], new_product_data['quantity'])
    
    def test_manager_user_can_patch_product(self) -> None:
        # Данные для частичного обновления товара
        new_product_data = {
            'price': 500,
            'quantity': 400,
        }

        # Частичное обновление товара админом и проверка
        patch_response = self.manager_client.patch(
            self.get_product_detail_url_with_slug(self.product1.slug),
            data=new_product_data, format='multipart',
        )
        self.assertEqual(patch_response.status_code, status.HTTP_200_OK)

        # Проверка на обновление товара в БД
        self.product1.refresh_from_db()
        self.check_product_from_db(
            slug=self.product1.slug,
            price=500,
            quantity=400,
        )

        # Взятие обновленного товара и проверка
        response = self.manager_client.get(
            self.get_product_detail_url_with_slug(self.product1.slug),
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Проверка обновленного товара
        self.assertEqual(Decimal(response.data['price']), Decimal(new_product_data['price']))
        self.assertEqual(response.data['quantity'], new_product_data['quantity'])

    def test_anon_user_cannot_delete_product(self) -> None:
        # Неправильное удаление товара анонимным пользователем и проверка
        wrong_anon_response = self.anon_client.delete(
            self.get_product_detail_url_with_slug(self.product1.slug),
        )
        self.assertEqual(wrong_anon_response.status_code, status.HTTP_401_UNAUTHORIZED)

        # Проверка на неудаление товара в БД
        self.assertTrue(Product.objects.filter(slug=self.product1.slug).exists())

    def test_normal_user_cannot_delete_product(self) -> None:
        # Неправильное удаление товара обычным пользователем и проверка
        wrong_normal_response = self.normal_client.delete(
            self.get_product_detail_url_with_slug(self.product1.slug),
        )
        self.assertEqual(wrong_normal_response.status_code, status.HTTP_403_FORBIDDEN)

        # Проверка на неудаление товара в БД
        self.assertTrue(Product.objects.filter(slug=self.product1.slug).exists())
    
    def test_admin_user_can_delete_product(self) -> None:
        # Удаление товара админом
        delete_response = self.admin_client.delete(
            self.get_product_detail_url_with_slug(self.product1.slug),
        )
        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)

        # Проверка на удаление товара в БД
        self.assertFalse(Product.objects.filter(slug=self.product1.slug).exists())

        # Проверка на наличие товара после удаления
        deleted_response = self.admin_client.get(
            self.get_product_detail_url_with_slug(self.product1.slug),
        )
        self.assertEqual(deleted_response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_manager_user_can_delete_product(self) -> None:
        # Удаление товара менеджером
        delete_response = self.manager_client.delete(
            self.get_product_detail_url_with_slug(self.product1.slug),
        )
        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)

        # Проверка на удаление товара в БД
        self.assertFalse(Product.objects.filter(slug=self.product1.slug).exists())

        # Проверка на наличие товара после удаления
        deleted_response = self.manager_client.get(
            self.get_product_detail_url_with_slug(self.product1.slug),
        )
        self.assertEqual(deleted_response.status_code, status.HTTP_404_NOT_FOUND)

    def test_anon_user_cannot_get_inactive_product_detail(self) -> None:
        # Создание неактивного товара анонимно
        inactive_product = Product.objects.create(**self.update_product_data(is_active=False))
        
        # Проверка товара в БД
        self.check_product_from_db(
            slug=inactive_product.slug, is_active=False,
        )

        # Неправильное получение неактивного товара анонимным пользователем и проверка
        wrong_anon_response = self.anon_client.get(
            self.get_product_detail_url_with_slug(inactive_product.slug),
        )
        self.assertEqual(wrong_anon_response.status_code, status.HTTP_404_NOT_FOUND)

    def test_normal_user_cannot_get_inactive_product_detail(self) -> None:
        # Создание неактивного товара обычным пользователем
        inactive_product = Product.objects.create(**self.update_product_data(is_active=False))

        # Проверка товара в БД
        self.check_product_from_db(slug=inactive_product.slug, is_active=False)

        # Неправильное получение неактивного товара обычным пользователем и проверка
        wrong_normal_response = self.normal_client.get(
            self.get_product_detail_url_with_slug(inactive_product.slug),
        )
        self.assertEqual(wrong_normal_response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_admin_user_can_get_inactive_product_detail(self) -> None:
        # Создание неактивного товара админом
        inactive_product = Product.objects.create(**self.update_product_data(is_active=False))

        # Проверка товара в БД
        self.check_product_from_db(slug=inactive_product.slug, is_active=False)

        # Попытка взять неактивный товар админом и проверка
        inactive_response = self.admin_client.get(
            self.get_product_detail_url_with_slug(inactive_product.slug),
        )
        self.assertEqual(inactive_response.status_code, status.HTTP_200_OK)

        # Попытка взять список, где есть неактивный товар и проверка
        inactive_list_response = self.admin_client.get(self.product_list_url)
        self.get_item_in_list(products_response=inactive_list_response, slug=inactive_product.slug)

    def test_manager_user_can_get_inactive_product_detail(self) -> None:
        # Создание неактивного товара менеджером
        inactive_product = Product.objects.create(**self.update_product_data(is_active=False))

        # Проверка товара в БД
        self.check_product_from_db(slug=inactive_product.slug, is_active=False)

        # Попытка взять неактивный товар менеджером и проверка
        inactive_response = self.manager_client.get(
            self.get_product_detail_url_with_slug(inactive_product.slug),
        )
        self.assertEqual(inactive_response.status_code, status.HTTP_200_OK)

        # Попытка взять список, где есть неактивный товар и проверка
        inactive_list_response = self.manager_client.get(self.product_list_url)
        self.get_item_in_list(products_response=inactive_list_response, slug=inactive_product.slug)

    def test_anon_user_cannot_get_inactive_product_in_product_list(self) -> None:
        # Создание обычного товара анонимно
        active_product = Product.objects.create(**self.update_product_data())

        # Создание неактивного товара анонимно
        inactive_product = Product.objects.create(**self.update_product_data(is_active=False))
        
        # Проверка товаров в БД
        self.check_product_from_db(
            slug=inactive_product.slug, is_active=False,
        )
        self.check_product_from_db(
            slug=active_product.slug, is_active=True,
        )

        # Получение списка товаров анонимно и проверка
        anon_product_list_response = self.anon_client.get(self.product_list_url)
        self.assertEqual(anon_product_list_response.status_code, status.HTTP_200_OK)

        # Проверка на наличие нужных слагов в списке товаров
        products_slugs = self.get_list_of_slugs(anon_product_list_response)
        self.assertIn(active_product.slug, products_slugs)
        self.assertNotIn(inactive_product.slug, products_slugs)
    
    def test_normal_user_cannot_get_inactive_product_in_product_list(self) -> None:
        # Создание обычного товара обычным пользователем
        active_product = Product.objects.create(**self.update_product_data())

        # Создание неактивного товара обычным пользователем
        inactive_product = Product.objects.create(**self.update_product_data(is_active=False))
        
        # Проверка товаров в БД
        self.check_product_from_db(
            slug=inactive_product.slug, is_active=False,
        )
        self.check_product_from_db(
            slug=active_product.slug, is_active=True,
        )

        # Получение списка товаров обычным пользователем и проверка
        normal_product_list_response = self.normal_client.get(self.product_list_url)
        self.assertEqual(normal_product_list_response.status_code, status.HTTP_200_OK)

        # Проверка на наличие нужных слагов в списке товаров
        products_slugs = self.get_list_of_slugs(normal_product_list_response)
        self.assertIn(active_product.slug, products_slugs)
        self.assertNotIn(inactive_product.slug, products_slugs)

    def test_admin_user_can_get_inactive_product_in_product_list(self) -> None:
        # Создание обычного товара админом
        active_product = Product.objects.create(**self.update_product_data())

        # Создание неактивного товара админом
        inactive_product = Product.objects.create(**self.update_product_data(is_active=False))
        
        # Проверка товаров в БД
        self.check_product_from_db(
            slug=inactive_product.slug, is_active=False,
        )
        self.check_product_from_db(
            slug=active_product.slug, is_active=True,
        )

        # Получение списка товаров админом и проверка
        admin_product_list_response = self.admin_client.get(self.product_list_url)
        self.assertEqual(admin_product_list_response.status_code, status.HTTP_200_OK)

        # Проверка на наличие нужных слагов в списке товаров
        products_slugs = self.get_list_of_slugs(admin_product_list_response)
        self.assertIn(active_product.slug, products_slugs)
        self.assertIn(inactive_product.slug, products_slugs)
    
    def test_manger_user_can_get_inactive_product_in_product_list(self) -> None:
        # Создание обычного товара менеджером
        active_product = Product.objects.create(**self.update_product_data())

        # Создание неактивного товара менеджером
        inactive_product = Product.objects.create(**self.update_product_data(is_active=False))
        
        # Проверка товаров в БД
        self.check_product_from_db(
            slug=inactive_product.slug, is_active=False,
        )
        self.check_product_from_db(
            slug=active_product.slug, is_active=True,
        )

        # Получение списка товаров менеджером и проверка
        admin_product_list_response = self.manager_client.get(self.product_list_url)
        self.assertEqual(admin_product_list_response.status_code, status.HTTP_200_OK)

        # Проверка на наличие нужных слагов в списке товаров
        products_slugs = self.get_list_of_slugs(admin_product_list_response)
        self.assertIn(active_product.slug, products_slugs)
        self.assertIn(inactive_product.slug, products_slugs)
