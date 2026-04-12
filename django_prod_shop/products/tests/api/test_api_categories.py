from uuid import uuid4

from django.core.cache import cache
from django.core.management import call_command
from django.contrib.auth import get_user_model
from django.urls import reverse

from rest_framework.test import APITestCase, APIClient
from rest_framework import status

from django_prod_shop.products.models import Category


user_model = get_user_model()


class CategoryAPITest(APITestCase):
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
        cls.category_list_url = reverse('products:category-list')

        ### Categories ###

        # Две стартовые категории
        cls.category1 = Category.objects.create(
            title='Test title of first category', slug='test-title-of-first-category', description='1'
        )
        cls.category2 = Category.objects.create(
            title='Test title of second category', slug='test-title-of-second-category', description='2'
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
    
    def get_category_detail_url_with_slug(self, slug):
        return reverse('products:category-detail', kwargs={'slug': slug})
    
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
    
    def get_list_items(self, categories_response):
        if 'results' in categories_response.data:
            return categories_response.data['results']
        return categories_response.data

    def get_list_of_slugs(self, categories_response):
        # Получение множества из слагов для избежания повторений
        return {item['slug'] for item in self.get_list_items(categories_response)}

    def get_item_in_list(self, categories_response, slug):
        # Проверка на наличие категории в ответе
        for item in self.get_list_items(categories_response):
            if item['slug'] == slug:
                return item
        self.fail(f"Категории со слагом '{slug}' не найдено")
    
    def update_category_data(self, **new_data):
        data = {
            'title': 'Test new title',
            'description': 'Test new description',
            'slug': f'test-new-title-{uuid4().hex[:8]}',
        }
        data.update(new_data)
        return data

    def check_contains_category_in_category_data(self, category_data, category):
        self.assertEqual(category_data['title'], category.title)
        self.assertEqual(category_data['description'], category.description)
        self.assertEqual(category_data['slug'], category.slug)
    
    def check_contains_category_in_created_category_response(self, created_category_data, category_data):
        self.assertEqual(created_category_data['title'], category_data['title'])
        self.assertEqual(created_category_data['description'], category_data['description'])
        self.assertEqual(created_category_data['slug'], category_data['slug'])

    def check_category_from_db(self, slug, data=None):
        # Проверка категории на создание в бд
        self.assertTrue(Category.objects.filter(slug=slug).exists())
        category = Category.objects.get(slug=slug)
        self.assertEqual(category.slug, slug)

        if data is None:
            return
        
        for key, value in data.items():
            self.assertTrue(hasattr(category, key))
            self.assertEqual(getattr(category, key), value)

    def test_anon_user_can_search_categories(self):
        # Получение второй категории по поиску по полю title
        searched_response = self.anon_client.get(f'{self.category_list_url}?search=second')

        # Получение слагов в ответе и проверка на совпадение и несовпадение категорий
        all_products_slugs = self.get_list_of_slugs(searched_response)
        self.assertIn(self.category2.slug, all_products_slugs)
        self.assertNotIn(self.category1.slug, all_products_slugs)

        # Получение первой категории по поиску по полю title
        searched_response = self.anon_client.get(f'{self.category_list_url}?search=first')

        # Получение слагов в ответе и проверка на совпадение и несовпадение категорий
        all_products_slugs = self.get_list_of_slugs(searched_response)
        self.assertIn(self.category1.slug, all_products_slugs)
        self.assertNotIn(self.category2.slug, all_products_slugs)

    def test_anon_user_can_get_category_list(self):
        # Взятие всех категорий и проверка
        list_response = self.anon_client.get(self.category_list_url)
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)

        # Получение и проверка первой категории
        category1_data = self.get_item_in_list(categories_response=list_response, slug=self.category1.slug)
        self.check_contains_category_in_category_data(category_data=category1_data, category=self.category1)

        # Получение и проверка второй категории
        category2_data = self.get_item_in_list(categories_response=list_response, slug=self.category2.slug)
        self.check_contains_category_in_category_data(category_data=category2_data, category=self.category2)

    def test_anon_user_can_get_category_detail(self):
        # Взятие категории и проверка
        detail_response = self.anon_client.get(
            self.get_category_detail_url_with_slug(slug=self.category1.slug),
        )
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)

        # Проверка на наличие в ответе
        self.check_contains_category_in_category_data(category_data=detail_response.data, category=self.category1)
    
    def test_anon_user_cannot_create_category(self):
        # Данные для создания категории
        category_data = self.update_category_data()

        # Попытка создать категорию анонимно и проверка
        wrong_anon_response = self.anon_client.post(
            self.category_list_url, data=category_data, format='json',
        )
        self.assertEqual(wrong_anon_response.status_code, status.HTTP_401_UNAUTHORIZED)

        # Проверка на несоздание категории
        self.assertFalse(Category.objects.filter(slug=category_data['slug']).exists())

    def test_normal_user_cannot_create_category(self):
        # Данные для создания категории
        category_data = self.update_category_data()

        # Попытка создать категорию обычному пользователю
        wrong_normal_response = self.client.post(
            self.category_list_url, data=category_data, format='json',
        )
        self.assertEqual(wrong_normal_response.status_code, status.HTTP_403_FORBIDDEN)

        # Проверка на несоздание категории
        self.assertFalse(Category.objects.filter(slug=category_data['slug']).exists())
    
    def test_admin_user_cannot_create_category_with_invalid_data(self):
        # Неправильные данные для создания категории
        wrong_category_data = {
            'description': 'Wrong description',
            'slug': 'wrong-slug',
        }

        # Неправильное создание категории и проврека
        wrong_response = self.admin_client.post(
            self.category_list_url, data=wrong_category_data, format='json',
        )
        self.assertEqual(wrong_response.status_code, status.HTTP_400_BAD_REQUEST)

        # Проверка на несоздание категории
        self.assertFalse(Category.objects.filter(slug=wrong_category_data['slug']).exists())

        # Неправильное взятие категории после создания и проверка
        wrong_response = self.admin_client.get(
            self.get_category_detail_url_with_slug(slug=wrong_category_data['slug']),
        )
        self.assertEqual(wrong_response.status_code, status.HTTP_404_NOT_FOUND)

    def test_admin_user_can_create_category(self):
        # Данные для создания категории
        category_data = self.update_category_data()

        # Создание категории админом и проверка
        created_response = self.admin_client.post(
            self.category_list_url, data=category_data, format='json',
        )
        self.assertEqual(created_response.status_code, status.HTTP_201_CREATED)

        # Проверка созданной категории
        self.check_contains_category_in_created_category_response(
            created_category_data=created_response.data, category_data=category_data
        )

        # Проверка на создание категории
        self.check_category_from_db(slug=category_data['slug'])

        # Взятие этой категории и проверка
        new_created_category_response = self.admin_client.get(
            self.get_category_detail_url_with_slug(slug=category_data['slug']),
        )
        self.assertEqual(new_created_category_response.status_code, status.HTTP_200_OK)

    def test_anon_user_cannot_put_category(self):
        # Данные для полного обновления категории
        new_category_data = self.update_category_data(
            title='New put test',
            slug='new-put-test',
        )

        # Неправильное польное обновлуние категории анонимным пользователем и проверка
        wrong_anon_response = self.anon_client.put(
            self.get_category_detail_url_with_slug(slug=self.category1.slug), 
            data=new_category_data, format='json',
        )
        self.assertEqual(wrong_anon_response.status_code, status.HTTP_401_UNAUTHORIZED)

        # Проверка на необновление категории
        self.assertFalse(Category.objects.filter(slug=new_category_data['slug']).exists())

    def test_normal_user_cannot_put_category(self):
        # Данные для полного обновления категории
        new_category_data = self.update_category_data(
            title='New put test',
            slug='new-put-test',
        )

        # Неправильное обновлкние категории обычным пользователем и проверка
        wrong_normal_response = self.client.put(
            self.get_category_detail_url_with_slug(slug=self.category1.slug),
            data=new_category_data, format='json',
        )
        self.assertEqual(wrong_normal_response.status_code, status.HTTP_403_FORBIDDEN)

        # Проверка на необновление категории
        self.assertFalse(Category.objects.filter(slug=new_category_data['slug']).exists())
    
    def test_admin_user_cannot_put_category_with_invalid_data(self):
        # Неправильные данные для полного обновления категории
        wrong_category_data = {
            'title': '',
            'slug': 'wrong-slug',
        }

        # Неправильное полное обновление админом
        wrong_response = self.admin_client.put(
            self.get_category_detail_url_with_slug(slug=self.category2.slug),
            data=wrong_category_data, format='json',
        )
        self.assertEqual(wrong_response.status_code, status.HTTP_400_BAD_REQUEST)

        # Проверка на необновление категории
        self.assertFalse(Category.objects.filter(slug=wrong_category_data['slug']).exists())

        # Неправильное взятие категории после полного обновления
        wrong_response = self.admin_client.get(
            self.get_category_detail_url_with_slug(slug=wrong_category_data['slug'])
        )
        self.assertEqual(wrong_response.status_code, status.HTTP_404_NOT_FOUND)

    def test_admin_user_can_put_category(self):
        # Данные для полного обновления категории
        new_category_data = self.update_category_data(
            title='New put test',
            slug='new-put-test',
        )

        # Старый слаг
        old_slug = self.category1.slug

        # Полное обновление категории админом и проверка
        put_response = self.admin_client.put(
            self.get_category_detail_url_with_slug(slug=self.category1.slug),
            data=new_category_data, format='json',
        )
        self.assertEqual(put_response.status_code, status.HTTP_200_OK)

        # Проверка на категорий в БД
        self.category1.refresh_from_db()
        self.assertTrue(Category.objects.filter(slug=new_category_data['slug']).exists())

        new_category = Category.objects.get(slug=new_category_data['slug'])
        self.assertEqual(new_category.slug, new_category_data['slug'])
        self.assertNotEqual(new_category.slug, old_slug)

        # Взятие новой категории и проверка
        category_response = self.admin_client.get(
            self.get_category_detail_url_with_slug(slug=new_category_data['slug']),
        )
        self.assertEqual(category_response.status_code, status.HTTP_200_OK)

        # Проверка новой категории
        self.check_contains_category_in_created_category_response(
            created_category_data=category_response.data, category_data=new_category_data,
        )

    def test_anon_user_cannot_patch_category(self):
        # Данные для частичного обновления категории
        new_category_data = {
            'title': 'New put title',
        }
        
        # Неправильное частичное обновление категории анонимным пользователем и проверка
        wrong_anon_response = self.anon_client.patch(
            self.get_category_detail_url_with_slug(slug=self.category1.slug), 
            data=new_category_data, format='json',
        )
        self.assertEqual(wrong_anon_response.status_code, status.HTTP_401_UNAUTHORIZED)

        # Проверка на необновление категории
        self.category1.refresh_from_db()
        self.check_category_from_db(
            slug=self.category1.slug, 
            data={'title': self.category1.title},
        )

    def test_normal_user_cannot_patch_category(self):
        # Данные для частичного обновления категории
        new_category_data = {
            'title': 'New put title',
        }

        # Неправильное частичное обновление категории обычным пользователем и проверка
        wrong_normal_response = self.client.patch(
            self.get_category_detail_url_with_slug(slug=self.category1.slug), 
            data=new_category_data, format='json',
        )
        self.assertEqual(wrong_normal_response.status_code, status.HTTP_403_FORBIDDEN)

        # Проверка на необновление категории
        self.category1.refresh_from_db()
        self.check_category_from_db(
            slug=self.category1.slug, 
            data={'title': self.category1.title},
        )

    def test_admin_user_cannot_patch_category_with_invalid_data(self):
        # Неправильные данные для частичного обновления категории
        wrong_category_data = self.update_category_data(
            title='',
        )

        # Неправильное частичное обновление категории и проврека
        wrong_response = self.admin_client.patch(
            self.get_category_detail_url_with_slug(slug=self.category1.slug), 
            data=wrong_category_data, format='json',
        )
        self.assertEqual(wrong_response.status_code, status.HTTP_400_BAD_REQUEST)

        # Проверка на необновление категории
        self.category1.refresh_from_db()
        self.check_category_from_db(
            slug=self.category1.slug, 
            data={'title': self.category1.title},
        )

        # Неправильное взятие категории после частичного обновления и проверка
        wrong_response = self.admin_client.get(
            self.get_category_detail_url_with_slug(slug=wrong_category_data['slug']),
        )
        self.assertEqual(wrong_response.status_code, status.HTTP_404_NOT_FOUND)

    def test_admin_user_can_patch_category(self):
        # Данные для частичного обновления категории
        new_category_data = {
            'title': 'New title',
        }

        # Частичное обновление категории админом и проверка
        patch_response = self.admin_client.patch(
            self.get_category_detail_url_with_slug(slug=self.category1.slug), 
            data=new_category_data, format='json',
        )
        self.assertEqual(patch_response.status_code, status.HTTP_200_OK)
        
        # Проверка на обновление категории
        self.category1.refresh_from_db()
        self.check_category_from_db(
            slug=new_category_data['slug'], 
            data={'title': new_category_data['title']},
        )

        # Взятие новой категории и проверка
        category_response = self.admin_client.get(
            self.get_category_detail_url_with_slug(slug=new_category_data['slug']),
        )
        self.assertEqual(category_response.status_code, status.HTTP_200_OK)

    def test_anon_user_cannot_delete_category(self):
        # Неправильное удаление категории анонимным пользователем и проврка
        wrong_anon_response = self.anon_client.delete(
            self.get_category_detail_url_with_slug(slug=self.category1.slug),
        )
        self.assertEqual(wrong_anon_response.status_code, status.HTTP_401_UNAUTHORIZED)

        # Проверка на неудаление
        self.assertTrue(Category.objects.filter(slug=self.category1.slug).exists())

    def test_normal_user_cannot_delete_category(self):
        # Неправильное удаление категории обычным пользователем и проврка
        wrong_normal_response = self.client.delete(
            self.get_category_detail_url_with_slug(slug=self.category1.slug),
        )
        self.assertEqual(wrong_normal_response.status_code, status.HTTP_403_FORBIDDEN)

        # Проверка на неудаление
        self.assertTrue(Category.objects.filter(slug=self.category1.slug).exists())

    def test_admin_user_can_delete_category(self):
        # Удалиение категории админом
        delete_response = self.admin_client.delete(
            self.get_category_detail_url_with_slug(slug=self.category1.slug), 
        )
        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)

        # Проверка на удаление
        self.assertFalse(Category.objects.filter(slug=self.category1.slug).exists())

        # Проверка на наличие удаленной категории
        deleted_response = self.admin_client.get(self.get_category_detail_url_with_slug(slug=self.category1.slug))
        self.assertEqual(deleted_response.status_code, status.HTTP_404_NOT_FOUND)
