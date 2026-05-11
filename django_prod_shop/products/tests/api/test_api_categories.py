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
        cls.category_list_url = reverse('products:category-list')

        ### Categories ###

        # Две стартовые категории
        cls.category1 = Category.objects.create(
            title='Test title of first category', slug='test-title-of-first-category', description='1'
        )
        cls.category2 = Category.objects.create(
            title='Test title of second category', slug='test-title-of-second-category', description='2'
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
    
    def get_category_detail_url_with_slug(self, slug: str) -> str:
        return reverse('products:category-detail', kwargs={'slug': slug})
    
    def get_list_items(self, categories_response: Response) -> list[dict[str, Any]]:
        if 'results' in categories_response.data:
            return categories_response.data['results']
        return categories_response.data

    def get_list_of_slugs(self, categories_response: Response) -> set[str]:
        # Получение множества из слагов для избежания повторений
        return {item['slug'] for item in self.get_list_items(categories_response)}

    def get_item_in_list(self, categories_response: Response, slug: str) -> dict[str, Any]:
        # Проверка на наличие категории в ответе
        for item in self.get_list_items(categories_response):
            if item['slug'] == slug:
                return item
        self.fail(f"Категории со слагом '{slug}' не найдено")
    
    def update_category_data(self, **new_data: Any) -> dict[str, Any]:
        data = {
            'title': 'Test new title',
            'description': 'Test new description',
            'slug': f'test-new-title-{uuid4().hex[:8]}',
        }
        data.update(new_data)
        return data

    def create_product_data(self, **new_data: Any) -> dict[str, Any]:
        data = {
            'title': 'Test new title',
            'category_id': self.category1.pk,
            'quantity': 100,
            'reserved_quantity': 15,
            'description': 'Test new description',
            'slug': f'test-new-title-{uuid4().hex[:8]}',
            'price': 9999,
            'is_active': True,
        }
        data.update(new_data)
        return data

    def check_contains_category_in_category_data(self, category_data: dict[str, Any], category: Category) -> None:
        self.assertEqual(category_data['title'], category.title)
        self.assertEqual(category_data['description'], category.description)
        self.assertEqual(category_data['slug'], category.slug)
    
    def check_contains_category_in_created_category_response(
            self, created_category_data: dict[str, Any], category_data: dict[str, Any],
        ) -> None:
        self.assertEqual(created_category_data['title'], category_data['title'])
        self.assertEqual(created_category_data['description'], category_data['description'])
        self.assertEqual(created_category_data['slug'], category_data['slug'])

    def check_category_from_db(self, slug: str, **data: Any) -> None:
        # Проверка категории на создание в бд
        self.assertTrue(Category.objects.filter(slug=slug).exists())
        category = Category.objects.get(slug=slug)
        self.assertEqual(category.slug, slug)
        
        for key, value in data.items():
            self.assertEqual(getattr(category, key), value)

    def test_anon_user_can_search_categories(self) -> None:
        # Получение второй категории по поиску по полю title и проверка
        searched_response = self.anon_client.get(f'{self.category_list_url}?search=second')
        self.assertEqual(searched_response.status_code, status.HTTP_200_OK)

        # Получение слагов в ответе и проверка на совпадение и несовпадение категорий
        all_categories_slugs = self.get_list_of_slugs(searched_response)
        self.assertIn(self.category2.slug, all_categories_slugs)
        self.assertNotIn(self.category1.slug, all_categories_slugs)

        # Получение первой категории по поиску по полю title и проверка
        searched_response = self.anon_client.get(f'{self.category_list_url}?search=first')
        self.assertEqual(searched_response.status_code, status.HTTP_200_OK)

        # Получение слагов в ответе и проверка на совпадение и несовпадение категорий
        all_categories_slugs = self.get_list_of_slugs(searched_response)
        self.assertIn(self.category1.slug, all_categories_slugs)
        self.assertNotIn(self.category2.slug, all_categories_slugs)

    def test_anon_user_can_get_category_list(self) -> None:
        # Взятие всех категорий и проверка
        list_response = self.anon_client.get(self.category_list_url)
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)

        # Получение и проверка первой категории
        category1_data = self.get_item_in_list(categories_response=list_response, slug=self.category1.slug)
        self.check_contains_category_in_category_data(category_data=category1_data, category=self.category1)

        # Получение и проверка второй категории
        category2_data = self.get_item_in_list(categories_response=list_response, slug=self.category2.slug)
        self.check_contains_category_in_category_data(category_data=category2_data, category=self.category2)

    def test_anon_user_can_get_category_detail(self) -> None:
        # Взятие категории и проверка
        detail_response = self.anon_client.get(
            self.get_category_detail_url_with_slug(slug=self.category1.slug),
        )
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)

        # Проверка на наличие в ответе
        self.check_contains_category_in_category_data(category_data=detail_response.data, category=self.category1)

    def test_anon_user_cannot_get_inactive_product_from_category_detail(self) -> None:
        # Создание активного товара
        active_product = Product.objects.create(**self.create_product_data(is_active=True))
        
        # Создание неактивного товара
        inactive_product = Product.objects.create(**self.create_product_data(is_active=False))

        # Получение детальной категории и проверка
        category_detail_response = self.anon_client.get(self.get_category_detail_url_with_slug(self.category1.slug))
        self.assertEqual(category_detail_response.status_code, status.HTTP_200_OK)

        # Проверка на наличие товаров в детальной категории
        product_slugs = {item['slug'] for item in category_detail_response.data['products']}
        self.assertIn(active_product.slug, product_slugs)
        self.assertNotIn(inactive_product.slug, product_slugs)

    def test_normal_user_cannot_get_inactive_product_from_category_detail(self) -> None:
        # Создание активного товара
        active_product = Product.objects.create(**self.create_product_data(is_active=True))
        
        # Создание неактивного товара
        inactive_product = Product.objects.create(**self.create_product_data(is_active=False))

        # Получение детальной категории и проверка
        category_detail_response = self.normal_client.get(self.get_category_detail_url_with_slug(self.category1.slug))
        self.assertEqual(category_detail_response.status_code, status.HTTP_200_OK)

        # Проверка на наличие товаров в детальной категории
        product_slugs = {item['slug'] for item in category_detail_response.data['products']}
        self.assertIn(active_product.slug, product_slugs)
        self.assertNotIn(inactive_product.slug, product_slugs)

    def test_admin_user_can_get_inactive_product_from_category_detail(self) -> None:
        # Создание неактивного товара
        inactive_product = Product.objects.create(**self.create_product_data(is_active=False))

        # Получение детальной категории и проверка
        category_detail_response = self.admin_client.get(self.get_category_detail_url_with_slug(self.category1.slug))
        self.assertEqual(category_detail_response.status_code, status.HTTP_200_OK)

        # Проверка на наличие товаров в детальной категории
        product_slugs = {item['slug'] for item in category_detail_response.data['products']}
        self.assertIn(inactive_product.slug, product_slugs)
    
    def test_manager_user_can_get_inactive_product_from_category_detail(self) -> None:
        # Создание неактивного товара
        inactive_product = Product.objects.create(**self.create_product_data(is_active=False))

        # Получение детальной категории и проверка
        category_detail_response = self.manager_client.get(self.get_category_detail_url_with_slug(self.category1.slug))
        self.assertEqual(category_detail_response.status_code, status.HTTP_200_OK)

        # Проверка на наличие товаров в детальной категории
        product_slugs = {item['slug'] for item in category_detail_response.data['products']}
        self.assertIn(inactive_product.slug, product_slugs)

    def test_anon_user_cannot_create_category(self) -> None:
        # Данные для создания категории
        category_data = self.update_category_data()

        # Попытка создать категорию анонимно и проверка
        wrong_anon_response = self.anon_client.post(
            self.category_list_url, data=category_data, format='json',
        )
        self.assertEqual(wrong_anon_response.status_code, status.HTTP_401_UNAUTHORIZED)

        # Проверка на несоздание категории
        self.assertFalse(Category.objects.filter(slug=category_data['slug']).exists())

    def test_normal_user_cannot_create_category(self) -> None:
        # Данные для создания категории
        category_data = self.update_category_data()

        # Попытка создать категорию обычному пользователю
        wrong_normal_response = self.normal_client.post(
            self.category_list_url, data=category_data, format='json',
        )
        self.assertEqual(wrong_normal_response.status_code, status.HTTP_403_FORBIDDEN)

        # Проверка на несоздание категории
        self.assertFalse(Category.objects.filter(slug=category_data['slug']).exists())
    
    def test_admin_user_cannot_create_category_with_invalid_data(self) -> None:
        # Неправильные данные для создания категории
        wrong_category_data = {
            'description': 'Wrong description',
            'slug': 'wrong-slug',
        }

        # Неправильное создание категории и проверека
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

    def test_admin_user_cannot_create_category_with_already_exists_slug(self) -> None:
        # Неправильные данные для создания категории
        wrong_category_data = self.update_category_data(slug=self.category1.slug)

        # Неправильное создание категории и проверека
        wrong_response = self.admin_client.post(
            self.category_list_url, data=wrong_category_data, format='json',
        )
        self.assertEqual(wrong_response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_admin_user_can_create_category(self) -> None:
        # Данные для создания категории
        category_data = self.update_category_data()

        # Создание категории админом и проверка
        created_response = self.admin_client.post(
            self.category_list_url, data=category_data, format='json',
        )
        self.assertEqual(created_response.status_code, status.HTTP_201_CREATED)

        # Проверка созданной категории
        self.check_contains_category_in_created_category_response(
            created_category_data=created_response.data, category_data=category_data,
        )

        # Проверка на создание категории
        self.check_category_from_db(slug=category_data['slug'])

        # Взятие этой категории и проверка
        new_created_category_response = self.admin_client.get(
            self.get_category_detail_url_with_slug(slug=category_data['slug']),
        )
        self.assertEqual(new_created_category_response.status_code, status.HTTP_200_OK)
    
    def test_manager_user_can_create_category(self) -> None:
        # Данные для создания категории
        category_data = self.update_category_data()

        # Создание категории менеджером и проверка
        created_response = self.manager_client.post(
            self.category_list_url, data=category_data, format='json',
        )
        self.assertEqual(created_response.status_code, status.HTTP_201_CREATED)

        # Проверка созданной категории
        self.check_contains_category_in_created_category_response(
            created_category_data=created_response.data, category_data=category_data,
        )

        # Проверка на создание категории
        self.check_category_from_db(slug=category_data['slug'])

        # Взятие этой категории и проверка
        new_created_category_response = self.manager_client.get(
            self.get_category_detail_url_with_slug(slug=category_data['slug']),
        )
        self.assertEqual(new_created_category_response.status_code, status.HTTP_200_OK)

    def test_anon_user_cannot_put_category(self) -> None:
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

    def test_normal_user_cannot_put_category(self) -> None:
        # Данные для полного обновления категории
        new_category_data = self.update_category_data(
            title='New put test',
            slug='new-put-test',
        )

        # Неправильное обновлкние категории обычным пользователем и проверка
        wrong_normal_response = self.normal_client.put(
            self.get_category_detail_url_with_slug(slug=self.category1.slug),
            data=new_category_data, format='json',
        )
        self.assertEqual(wrong_normal_response.status_code, status.HTTP_403_FORBIDDEN)

        # Проверка на необновление категории
        self.assertFalse(Category.objects.filter(slug=new_category_data['slug']).exists())
    
    def test_admin_user_cannot_put_category_with_invalid_data(self) -> None:
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
    
    def test_admin_user_cannot_put_category_with_already_exists_slug(self) -> None:
        # Неправильные данные для полного обновления категории
        wrong_category_data = self.update_category_data(slug=self.category2.slug)

        # Неправильное полное обновление админом
        wrong_response = self.admin_client.put(
            self.get_category_detail_url_with_slug(slug=self.category1.slug),
            data=wrong_category_data, format='json',
        )
        self.assertEqual(wrong_response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_admin_user_can_put_category(self) -> None:
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
    
    def test_manager_user_can_put_category(self) -> None:
        # Данные для полного обновления категории
        new_category_data = self.update_category_data(
            title='New put test',
            slug='new-put-test',
        )

        # Старый слаг
        old_slug = self.category1.slug

        # Полное обновление категории менеджером и проверка
        put_response = self.manager_client.put(
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
        category_response = self.manager_client.get(
            self.get_category_detail_url_with_slug(slug=new_category_data['slug']),
        )
        self.assertEqual(category_response.status_code, status.HTTP_200_OK)

        # Проверка новой категории
        self.check_contains_category_in_created_category_response(
            created_category_data=category_response.data, category_data=new_category_data,
        )

    def test_anon_user_cannot_patch_category(self) -> None:
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
            title=self.category1.title,
        )

    def test_normal_user_cannot_patch_category(self) -> None:
        # Данные для частичного обновления категории
        new_category_data = {
            'title': 'New put title',
        }

        # Неправильное частичное обновление категории обычным пользователем и проверка
        wrong_normal_response = self.normal_client.patch(
            self.get_category_detail_url_with_slug(slug=self.category1.slug), 
            data=new_category_data, format='json',
        )
        self.assertEqual(wrong_normal_response.status_code, status.HTTP_403_FORBIDDEN)

        # Проверка на необновление категории
        self.category1.refresh_from_db()
        self.check_category_from_db(
            slug=self.category1.slug, 
            title=self.category1.title,
        )

    def test_admin_user_cannot_patch_category_with_invalid_data(self) -> None:
        # Неправильные данные для частичного обновления категории
        wrong_category_data = self.update_category_data(
            title='',
        )

        # Неправильное частичное обновление категории и проверека
        wrong_response = self.admin_client.patch(
            self.get_category_detail_url_with_slug(slug=self.category1.slug), 
            data=wrong_category_data, format='json',
        )
        self.assertEqual(wrong_response.status_code, status.HTTP_400_BAD_REQUEST)

        # Проверка на необновление категории
        self.category1.refresh_from_db()
        self.check_category_from_db(
            slug=self.category1.slug, 
            title=self.category1.title,
        )

        # Неправильное взятие категории после частичного обновления и проверка
        wrong_response = self.admin_client.get(
            self.get_category_detail_url_with_slug(slug=wrong_category_data['slug']),
        )
        self.assertEqual(wrong_response.status_code, status.HTTP_404_NOT_FOUND)

    def test_admin_user_can_patch_category(self) -> None:
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
            slug=self.category1.slug, 
            title=new_category_data['title'],
        )

        # Взятие новой категории и проверка
        category_response = self.admin_client.get(
            self.get_category_detail_url_with_slug(slug=self.category1.slug),
        )
        self.assertEqual(category_response.status_code, status.HTTP_200_OK)
    
    def test_manager_user_can_patch_category(self) -> None:
        # Данные для частичного обновления категории
        new_category_data = {
            'title': 'New title',
        }

        # Частичное обновление категории менеджером и проверка
        patch_response = self.manager_client.patch(
            self.get_category_detail_url_with_slug(slug=self.category1.slug), 
            data=new_category_data, format='json',
        )
        self.assertEqual(patch_response.status_code, status.HTTP_200_OK)
        
        # Проверка на обновление категории
        self.category1.refresh_from_db()
        self.check_category_from_db(
            slug=self.category1.slug, 
            title=new_category_data['title'],
        )

        # Взятие новой категории и проверка
        category_response = self.manager_client.get(
            self.get_category_detail_url_with_slug(slug=self.category1.slug),
        )
        self.assertEqual(category_response.status_code, status.HTTP_200_OK)

    def test_anon_user_cannot_delete_category(self) -> None:
        # Неправильное удаление категории анонимным пользователем и проверка
        wrong_anon_response = self.anon_client.delete(
            self.get_category_detail_url_with_slug(slug=self.category1.slug),
        )
        self.assertEqual(wrong_anon_response.status_code, status.HTTP_401_UNAUTHORIZED)

        # Проверка на неудаление
        self.assertTrue(Category.objects.filter(slug=self.category1.slug).exists())

    def test_normal_user_cannot_delete_category(self) -> None:
        # Неправильное удаление категории обычным пользователем и проверка
        wrong_normal_response = self.normal_client.delete(
            self.get_category_detail_url_with_slug(slug=self.category1.slug),
        )
        self.assertEqual(wrong_normal_response.status_code, status.HTTP_403_FORBIDDEN)

        # Проверка на неудаление
        self.assertTrue(Category.objects.filter(slug=self.category1.slug).exists())

    def test_admin_user_can_delete_category(self) -> None:
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
    
    def test_manager_user_can_delete_category(self) -> None:
        # Удалиение категории менеджером
        delete_response = self.manager_client.delete(
            self.get_category_detail_url_with_slug(slug=self.category1.slug), 
        )
        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)

        # Проверка на удаление
        self.assertFalse(Category.objects.filter(slug=self.category1.slug).exists())

        # Проверка на наличие удаленной категории
        deleted_response = self.manager_client.get(self.get_category_detail_url_with_slug(slug=self.category1.slug))
        self.assertEqual(deleted_response.status_code, status.HTTP_404_NOT_FOUND)
