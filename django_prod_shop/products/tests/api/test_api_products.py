from decimal import Decimal
from uuid import uuid4

from django.core.cache import cache
from django.core.management import call_command
from django.contrib.auth import get_user_model
from django.urls import reverse

from rest_framework.test import APITestCase, APIClient
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
        user_model.objects.create_user(
            email=cls.normal_user_data['email'], 
            password=cls.normal_user_data['password'],
            is_active=True,
        )

        # Создание админа (суперюзера)
        cls.admin_user_data = {
            'email': 'admin@mail.ru',
            'password': 'admin_password!',
        }
        user_model.objects.create_superuser(
            email=cls.admin_user_data['email'], 
            password=cls.admin_user_data['password'],
            is_active=True,
        )

        # Объявление url
        cls.token_create_url = reverse('users:token-access')
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

    def setUp(self):
        cache.clear()
        self.admin_client = APIClient()
        self.anon_client = APIClient()

        # Авторизация админа и обычного пользователя
        self.login_user(
            email=self.normal_user_data['email'],
            password=self.normal_user_data['password'],
            client=self.client,
        )
        self.login_user(
            email=self.admin_user_data['email'],
            password=self.admin_user_data['password'],
            client=self.admin_client,
        )
    
    def get_product_detail_url_with_slug(self, slug):
        return reverse('products:product-detail', kwargs={'slug': slug})
    
    def login_user(self, email, password, client=None):
        # Логин пользователя
        if client is None:
            client = self.client
        
        response = client.post(
            self.token_create_url,
            data={
                'email': email,
                'password': password,
            },
            format='json',
        )
    
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)

        client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")

        return response

    def get_list_items(self, products_response):
        if 'results' in products_response.data:
            return products_response.data['results']
        return products_response.data

    def get_list_of_slugs(self, products_response):
        # Получение множества из слагов для избежания повторений
        return {item['slug'] for item in self.get_list_items(products_response)}

    def get_item_in_list(self, products_response, slug):
        # Проверка на наличие товара в ответе
        for item in self.get_list_items(products_response):
            if item['slug'] == slug:
                return item
        self.fail(f"Товара со слагом '{slug}' не найдено")

    def update_product_data(self, **new_data):
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

    def check_contains_product_in_product_data(self, product_data, product):
        self.assertEqual(product_data['title'], product.title)
        self.assertEqual(Decimal(product_data['price']), Decimal(product.price))
        self.assertEqual(product_data['category_name'], product.category.title)
        self.assertEqual(product_data['quantity'], product.quantity)
        self.assertEqual(product_data['reserved_quantity'], product.reserved_quantity)
    
    def check_contains_product_in_created_product_response(self, created_product_data, product_data):
        self.assertEqual(created_product_data['title'], product_data['title'])
        self.assertEqual(Decimal(created_product_data['price']), Decimal(product_data['price']))
        self.assertEqual(created_product_data['slug'], product_data['slug'])
        self.assertEqual(created_product_data['quantity'], product_data['quantity'])
        self.assertEqual(
            created_product_data['reserved_quantity'], product_data['reserved_quantity']
        )

    def check_product_from_db(self, slug, data=None):
        # Проверка товара на создание в бд
        self.assertTrue(Product.objects.filter(slug=slug).exists())
        product = Product.objects.get(slug=slug)
        self.assertEqual(product.slug, slug)

        if data is None:
            return
        
        for key, value in data.items():
            self.assertTrue(hasattr(product, key))
            if key == 'price':
                self.assertEqual(Decimal(getattr(product, key)), Decimal(value))
            else:
                self.assertEqual(getattr(product, key), value)

    def test_ordering_product_by_anon_user(self):
        # Создание нового товара
        new_product = Product.objects.create(**self.update_product_data())

        # Получение списка товаров и проверка
        ordering_response = self.anon_client.get(self.product_list_url)
        self.assertEqual(ordering_response.status_code, status.HTTP_200_OK)

        # Получение товара из списка и проверка
        product_list = self.get_list_items(ordering_response)
        self.assertEqual(product_list[0]['slug'], new_product.slug)

    def test_get_products_search_category_title_list_by_anon_user(self):
        # Получение второго товара по поиску по полю title и проверка
        searched_response = self.anon_client.get(f'{self.product_list_url}?search={self.category.title}')
        self.assertEqual(searched_response.status_code, status.HTTP_200_OK)
        
        # Получение слагов в ответе и проверка на совпадение и несовпадение товаров
        all_products_slugs = self.get_list_of_slugs(searched_response)
        self.assertIn(self.product1.slug, all_products_slugs)
        self.assertIn(self.product2.slug, all_products_slugs)

    def test_get_products_search_title_list_by_anon_user(self):
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

    def test_get_products_filter_list_by_anon_user(self):
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
    
    def test_get_list_of_products_by_anon_user(self):
        # Получение всех товаров и проверка
        list_response = self.anon_client.get(self.product_list_url)
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)

        # Получение и проверка первого товара
        product1_data = self.get_item_in_list(products_response=list_response, slug=self.product1.slug)
        self.check_contains_product_in_product_data(product_data=product1_data, product=self.product1)

        # Получение и проверка второго товара
        product2_data = self.get_item_in_list(products_response=list_response, slug=self.product2.slug)
        self.check_contains_product_in_product_data(product_data=product2_data, product=self.product2)
    
    def test_get_detail_product_by_anon_user(self):
        # Взятие товара и проверка
        detail_response = self.anon_client.get(
            self.get_product_detail_url_with_slug(self.product1.slug)
        )
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)

        # Проверка товара
        self.check_contains_product_in_product_data(
            product_data=detail_response.data, product=self.product1,
        )

    def test_get_wrong_detail_product_by_anon_user(self):
        # Неправильное взятие товара и проверка
        wrong_detail_response = self.anon_client.get(
            self.get_product_detail_url_with_slug('wrong-slug')
        )
        self.assertEqual(wrong_detail_response.status_code, status.HTTP_404_NOT_FOUND)

    def test_wrong_create_product_by_anon_user(self):
        # Данные для создания товара
        product_data = self.update_product_data()

        # Неправильная попытка создать товар анонимно
        wrong_anon_response = self.anon_client.post(
            self.product_list_url, data=product_data, format='json',
        )
        self.assertEqual(wrong_anon_response.status_code, status.HTTP_401_UNAUTHORIZED)

        # Проверка на неcоздание товара
        self.assertFalse(Product.objects.filter(slug=product_data['slug']).exists())

    def test_wrong_create_product_by_normal_user(self):
        # Данные для создания товара
        product_data = self.update_product_data()

        # Неправильная попытка создать товар обычному пользователю
        wrong_normal_response = self.client.post(
            self.product_list_url, data=product_data, format='json',
        )
        self.assertEqual(wrong_normal_response.status_code, status.HTTP_403_FORBIDDEN)

        # Проверка на неcоздание товара
        self.assertFalse(Product.objects.filter(slug=product_data['slug']).exists())

    def test_wrong_create_product_and_get_it_by_admin_user(self):
        # Неправильные данные для создания товара
        wrong_product_data = {
            'title': 'Wrong title',
            'description': 'Wrong description',
            'slug': 'wrong-title',
        }

        # Неправильная попытка создать товар админом и проверка
        wrong_response = self.admin_client.post(
            self.product_list_url, data=wrong_product_data, format='json',
        )
        self.assertEqual(wrong_response.status_code, status.HTTP_400_BAD_REQUEST)

        # Проверка на неcоздание товара
        self.assertFalse(Product.objects.filter(slug=wrong_product_data['slug']).exists())

        # Взятие несуществующего товара после попытки создания и проверка
        wrong_product_detail_response = self.client.get(
            self.get_product_detail_url_with_slug(wrong_product_data['slug'])
        )
        self.assertEqual(wrong_product_detail_response.status_code, status.HTTP_404_NOT_FOUND)

    def test_right_create_product_and_get_it_by_admin_user(self):
        # Данные для создания товара
        product_data = self.update_product_data()

        # Создание товара админом и проверка
        new_created_product_response = self.admin_client.post(
            self.product_list_url, data=product_data, format='json',
        )
        self.assertEqual(new_created_product_response.status_code, status.HTTP_201_CREATED)
        
        # Проверка товара в БД
        self.check_product_from_db(slug=product_data['slug'])

        # Проверка созданного товара
        self.check_contains_product_in_created_product_response(
            created_product_data=new_created_product_response.data, product_data=product_data,
        )

        # Взятие нового товара и проверка
        new_product = Product.objects.get(slug=product_data['slug'])
        new_product_response = self.client.get(
            self.get_product_detail_url_with_slug(new_product.slug)
        )
        self.assertEqual(new_product_response.status_code, status.HTTP_200_OK)

        # Проверка нового товара
        self.check_contains_product_in_product_data(
            product_data=new_product_response.data, product=new_product,
        )

    def test_wrong_create_product_with_price_lt_0_by_admin_user(self):
        # Неправильные данные для создания товара
        wrong_product_data = self.update_product_data(price=-999)

        # Неправильная попытка создать товар админом и проверка
        wrong_response = self.admin_client.post(
            self.product_list_url, data=wrong_product_data, format='json',
        )
        self.assertEqual(wrong_response.status_code, status.HTTP_400_BAD_REQUEST)

        # Проверка на неcоздание товара
        self.assertFalse(Product.objects.filter(slug=wrong_product_data['slug']).exists())
    
    def test_wrong_create_product_with_quantity_lt_reserved_quantity_by_admin_user(self):
        # Неправильные данные для создания товара
        wrong_product_data = self.update_product_data(quantity=10, reserved_quantity=20)

        # Неправильная попытка создать товар админом и проверка
        wrong_response = self.admin_client.post(
            self.product_list_url, data=wrong_product_data, format='json',
        )
        self.assertEqual(wrong_response.status_code, status.HTTP_400_BAD_REQUEST)

        # Проверка на неcоздание товара
        self.assertFalse(Product.objects.filter(slug=wrong_product_data['slug']).exists())

    def test_wrong_put_product_by_anon_user(self):
        # Данные для полного обновления товара
        new_product_data = self.update_product_data()

        # Неправильная попытка обновить товар анонимно и проверка
        wrong_anon_response = self.anon_client.put(
            self.get_product_detail_url_with_slug(self.product1.slug), 
            data=new_product_data, format='json',
        )
        self.assertEqual(wrong_anon_response.status_code, status.HTTP_401_UNAUTHORIZED)
        
        # Проверка на необновление товара
        self.product1.refresh_from_db()
        self.assertFalse(Product.objects.filter(slug=new_product_data['slug']).exists())

    def test_wrong_put_product_by_normal_user(self):
        # Данные для полного обновления товара
        new_product_data = self.update_product_data()

        # Неправильная попытка обновить товар обычному пользователю  и проверка
        wrong_normal_response = self.client.put(
            self.get_product_detail_url_with_slug(self.product1.slug), 
            data=new_product_data, format='json',
        )
        self.assertEqual(wrong_normal_response.status_code, status.HTTP_403_FORBIDDEN)

        # Проверка на необновление товара
        self.product1.refresh_from_db()
        self.assertFalse(Product.objects.filter(slug=new_product_data['slug']).exists())

    def test_wrong_put_product_by_admin_user(self):
        # Неправильные данные для полного обновления
        wrong_product_data = {
            'description': 'Wrong description',
            'slug': 'wrong-slug',
        }

        # Неправильное полное обновление товара админом и проверка
        wrong_response = self.admin_client.put(
            self.get_product_detail_url_with_slug(self.product1.slug), 
            data=wrong_product_data, format='json',
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

    def test_right_put_product_by_admin_user(self):
        # Данные для полного обновления товара
        new_product_data = self.update_product_data()

        # Старый слаг
        old_slug = self.product1.slug

        # Полное обновление товара админом и проверка
        put_response = self.admin_client.put(
            self.get_product_detail_url_with_slug(self.product1.slug), 
            data=new_product_data, format='json',
        )
        self.assertEqual(put_response.status_code, status.HTTP_200_OK)
        
        # Проверка на товаров в БД
        self.product1.refresh_from_db()
        self.assertTrue(Product.objects.filter(slug=new_product_data['slug']).exists())

        new_product = Product.objects.get(slug=new_product_data['slug'])
        self.assertEqual(new_product.slug, new_product_data['slug'])
        self.assertNotEqual(new_product.slug, old_slug)
        
        # Взятие нового товара и проверка
        product_response = self.client.get(
            self.get_product_detail_url_with_slug(new_product_data['slug'])
        )
        self.assertEqual(product_response.status_code, status.HTTP_200_OK)

        # Проверка нового товара
        self.check_contains_product_in_created_product_response(
            created_product_data=product_response.data, product_data=new_product_data,
        )
    
    def test_wrong_patch_product_by_anon_user(self):
        # Данные для частичного обновления товара
        new_product_data = {
            'price': 500,
            'quantity': 400,
        }

        # Неправильное частичное обновление товара анонимным пользователем и проверка
        wrong_anon_response = self.anon_client.patch(
            self.get_product_detail_url_with_slug(self.product1.slug), 
            data=new_product_data, format='json',
        )
        self.assertEqual(wrong_anon_response.status_code, status.HTTP_401_UNAUTHORIZED)

        # Проверка на необновление товара в БД
        self.product1.refresh_from_db()
        self.check_product_from_db(
            slug=self.product1.slug, 
            data={'price': self.product1.price, 'quantity': self.product1.quantity}
        )

    def test_wrong_patch_product_by_normal_user(self):
        # Данные для частичного обновления товара
        new_product_data = {
            'price': 500,
            'quantity': 400,
        }

        # Неправильное частичное обновление товара обычным пользователем и проверка
        wrong_normal_response = self.client.patch(
            self.get_product_detail_url_with_slug(self.product1.slug),  
            data=new_product_data, format='json',
        )
        self.assertEqual(wrong_normal_response.status_code, status.HTTP_403_FORBIDDEN)

        # Проверка на необновление товара в БД
        self.product1.refresh_from_db()
        self.check_product_from_db(
            slug=self.product1.slug, 
            data={'price': self.product1.price, 'quantity': self.product1.quantity}
        )

    def test_wrong_patch_product_by_admin_user(self):
        # Неправильные данные для частичного обновления
        wrong_product_data = {
            'title': '',
            'description': 'Wrong description',
            'slug': 'wrong-slug',
        }

        # Неправильное частичное обновление товара и проверка
        wrong_patch_response = self.admin_client.patch(
            self.get_product_detail_url_with_slug(self.product1.slug), 
            data=wrong_product_data, format='json',
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

    def test_right_patch_product_by_admin_user(self):
        # Данные для частичного обновления товара
        new_product_data = {
            'price': 500,
            'quantity': 400,
        }

        # Частичное обновление товара админом и проверка
        patch_response = self.admin_client.patch(
            self.get_product_detail_url_with_slug(self.product1.slug),
            data=new_product_data, format='json',
        )
        self.assertEqual(patch_response.status_code, status.HTTP_200_OK)

        # Проверка на обновление товара в БД
        self.product1.refresh_from_db()
        self.check_product_from_db(slug=self.product1.slug, data={'price': 500, 'quantity': 400})

        # Взятие обновленного товара и проверка
        response = self.client.get(
            self.get_product_detail_url_with_slug(self.product1.slug),
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Проверка обновленного товара
        self.assertEqual(Decimal(response.data['price']), Decimal(new_product_data['price']))
        self.assertEqual(response.data['quantity'], new_product_data['quantity'])

    def test_wrong_delete_product_by_anon_user(self):
        # Неправильное удаление товара анонимным пользователем и проверка
        wrong_anon_response = self.anon_client.delete(
            self.get_product_detail_url_with_slug(self.product1.slug),
        )
        self.assertEqual(wrong_anon_response.status_code, status.HTTP_401_UNAUTHORIZED)

        # Проверка на неудаление товара в БД
        self.assertTrue(Product.objects.filter(slug=self.product1.slug).exists())

    def test_wrong_delete_product_by_normal_user(self):
        # Неправильное удаление товара обычным пользователем и проверка
        wrong_normal_response = self.client.delete(
            self.get_product_detail_url_with_slug(self.product1.slug),
        )
        self.assertEqual(wrong_normal_response.status_code, status.HTTP_403_FORBIDDEN)

        # Проверка на неудаление товара в БД
        self.assertTrue(Product.objects.filter(slug=self.product1.slug).exists())
    
    def test_delete_product_by_admin_user(self):
        # Удаление товара админом
        delete_response = self.admin_client.delete(
            self.get_product_detail_url_with_slug(self.product1.slug),
        )
        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)

        # Проверка на удаление товара в БД
        self.assertFalse(Product.objects.filter(slug=self.product1.slug).exists())

        # Проверка на наличие товара после удаления
        deleted_response = self.client.get(
            self.get_product_detail_url_with_slug(self.product1.slug),
        )
        self.assertEqual(deleted_response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_in_active_product_by_anon_user(self):
        # Создание неактивного товара
        in_active_product = Product.objects.create(**self.update_product_data(is_active=False))
        
        # Проверка товара в БД
        self.check_product_from_db(slug=in_active_product.slug, data={'is_active': False})

        # Неправильное получение неактивного товара анонимным пользователем и проверка
        wrong_anon_response = self.anon_client.get(
            self.get_product_detail_url_with_slug(in_active_product.slug),
        )
        self.assertEqual(wrong_anon_response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_in_active_product_by_normal_user(self):
        # Создание неактивного товара
        in_active_product = Product.objects.create(**self.update_product_data(is_active=False))

        # Проверка товара в БД
        self.check_product_from_db(slug=in_active_product.slug, data={'is_active': False})

        # Неправильное получение неактивного товара обычным пользователем и проверка
        wrong_normal_response = self.client.get(
            self.get_product_detail_url_with_slug(in_active_product.slug),
        )
        self.assertEqual(wrong_normal_response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_get_in_active_product_by_admin_user(self):
        # Создание неактивного товара
        in_active_product = Product.objects.create(**self.update_product_data(is_active=False))

        # Проверка товара в БД
        self.check_product_from_db(slug=in_active_product.slug, data={'is_active': False})

        # Попытка взять неактивный товар и проверка
        in_active_response = self.admin_client.get(
            self.get_product_detail_url_with_slug(in_active_product.slug),
        )
        self.assertEqual(in_active_response.status_code, status.HTTP_200_OK)

        # Попытка взять список, где есть неактивный товар и проверка
        in_active_list_response = self.admin_client.get(self.product_list_url)
        self.get_item_in_list(products_response=in_active_list_response, slug=in_active_product.slug)
