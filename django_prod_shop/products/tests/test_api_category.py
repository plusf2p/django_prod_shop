from django.test import TestCase
from django.urls import reverse

from rest_framework import status

from django_prod_shop.products.models import Category


class CategoryTest(TestCase):
    def setUp(self):
        Category.objects.create(
            title='Test title of first category', slug='test-title-of-first-category', description='1'
        )
        Category.objects.create(
            title='Test title of second category', slug='test-title-of-second-category', description='2'
        )

    def test_get_categories_with_api_requests(self):
        # Взятие всех объектов Category
        response = self.client.get(reverse('products:category-list'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        print(response)

        self.assertContains(response, 'Test title of first category')
        self.assertContains(response, 'Test title of second category')

        category = Category.objects.filter(title='Test title of first category').first()
        response = self.client.get(reverse('products:category-detail', kwargs={'pk': category.pk}))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        print(response)

        self.assertContains(response, 'Test title of first category')


    # def test_create_categories_with_api_requests(self):
    #     # Создание 1 объекта за раз
    #     category_data = {
    #         'title': 'Test api title',
    #         'slug': 'test-api-title',
    #         'description': '',
    #     }

    #     response = self.client.post(reverse('products:category-list'), data=category_data)
        

