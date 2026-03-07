from django.urls import reverse
from django.shortcuts import get_object_or_404

from rest_framework.test import APITestCase
from rest_framework import status

from django_prod_shop.products.models import Category


class CategoryAPITest(APITestCase):
    def setUp(self):
        # Два стартовых объекта Category
        self.category1 = Category.objects.create(
            title='Test title of first category', slug='test-title-of-first-category', description='1'
        )
        self.category2 = Category.objects.create(
            title='Test title of second category', slug='test-title-of-second-category', description='2'
        )

    def test_get_list_and_partial_categories(self):
        # Взятие всех объектов Category
        response = self.client.get(reverse('products:category-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertContains(response, self.category1.title)
        self.assertContains(response, self.category1.slug)

        self.assertContains(response, self.category2.title)
        self.assertContains(response, self.category2.slug)

        # Взятие одного объекта Category
        response = self.client.get(reverse('products:category-detail', kwargs={'slug': self.category1.slug}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertContains(response, self.category1.title)
        self.assertContains(response, self.category1.slug)

        # Неправильное взятие одного объекта Category
        response = self.client.get(reverse('products:category-detail', kwargs={'slug': 'wrong-slug'}))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_post_create_and_get_partial_category(self):
        # Создание одного объекта Category
        category_data = {
            'title': 'Test create title',
            'description': 'Test create description',
            'slug': 'test-create-title',
        }
        response = self.client.post(reverse('products:category-list'), data=category_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Проверка созданного объекта
        self.assertEqual(response.data.get('title'), category_data.get('title'))
        self.assertEqual(response.data.get('slug'), category_data.get('slug'))
        self.assertEqual(response.data.get('description'), category_data.get('description'))

        # Взятие этого объекта Category и его повторная проверка
        new_category = get_object_or_404(Category, slug=category_data.get('slug'))

        response = self.client.get(reverse('products:category-detail', kwargs={'slug': new_category.slug}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertContains(response, new_category.title)
        self.assertContains(response, new_category.slug)

        # Неправильное создание одного объекта Category
        wrong_category_data = {
            'description': 'Wrong description',
            'slug': 'wrong-slug',
        }
        response = self.client.post(reverse('products:category-list'), data=wrong_category_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Неправильное взятие одного объекта Category после создания
        response = self.client.get(reverse('products:category-detail', kwargs={'slug': wrong_category_data.get('slug')}))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_put_partial_category(self):
        # Полное обновление одного объекта Category
        new_category_data = {
            'title': 'New put test',
            'description': 'New put description',
            'slug': 'new-put-test',
        }
        response = self.client.put(reverse('products:category-detail', kwargs={'slug': self.category1.slug}), data=new_category_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Взятие нового объекта
        response = self.client.get(reverse('products:category-detail', kwargs={'slug': new_category_data.get('slug')}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Проверка нового объекта
        self.assertEqual(response.data.get('title'), new_category_data.get('title'))
        self.assertEqual(response.data.get('slug'), new_category_data.get('slug'))

        # Неправильное полное обновление одного объекта Category
        wrong_category_data = {
            'description': 'Wrong description',
            'slug': 'wrong-slug',
        }
        response = self.client.put(reverse('products:category-detail', kwargs={'slug': self.category2.slug}), data=wrong_category_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Неправильное взятие одного объекта Category после полного обновления
        response = self.client.get(reverse('products:category-detail', kwargs={'slug': wrong_category_data.get('slug')}))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_patch_partial_category(self):
        # Получение существующего объекта Category
        response = self.client.get(reverse('products:category-detail', kwargs={'slug': self.category1.slug}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Частичное обновление одного объекта Category
        new_category_data = {
            'title': response.data.get('title'),
            'description': 'New put description',
            'slug': response.data.get('slug'),
        }
        response = self.client.patch(reverse('products:category-detail', kwargs={'slug': self.category1.slug}), data=new_category_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Взятие нового объекта
        response = self.client.get(reverse('products:category-detail', kwargs={'slug': new_category_data.get('slug')}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Проверка нового объекта
        self.assertEqual(response.data.get('title'), new_category_data.get('title'))
        self.assertEqual(response.data.get('slug'), new_category_data.get('slug'))
    
        # Неправильное частичное обновление одного объекта Category
        response = self.client.get(reverse('products:category-detail', kwargs={'slug': self.category2.slug}))
        wrong_category_data = {
            'title': '',
            'description': 'Wrong description',
            'slug': 'wrong-slug',
        }
        response = self.client.patch(reverse('products:category-detail', kwargs={'slug': self.category2.slug}), data=wrong_category_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Неправильное взятие одного объекта Category после частичного обновления
        response = self.client.get(reverse('products:category-detail', kwargs={'slug': wrong_category_data.get('slug')}))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_partial_category(self):
        # Удаление стартового объекта Category
        response = self.client.delete(reverse('products:category-detail', kwargs={'slug': self.category1.slug}))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Проверка на наличие стартового удаленного объекта Category
        response = self.client.get(reverse('products:category-detail', kwargs={'slug': self.category1.slug}))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
