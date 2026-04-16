from datetime import timedelta

from django.urls import reverse
from django.utils import timezone
from django.core.management import call_command
from django.core.cache import cache
from django.contrib.auth import get_user_model

from rest_framework.test import APITestCase, APIClient
from rest_framework import status

from django_prod_shop.coupons.models import Coupon


user_model = get_user_model()


class CouponAPITest(APITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        # Создание ролей
        call_command('create_groups')

        ### Users ###

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
        cls.list_coupons_url = reverse('coupons:coupons-list')

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
        
    def setUp(self):
        cache.clear()
        self.admin_client = APIClient()
        self.normal_client = APIClient()
        self.anon_client = APIClient()

        # Авторизация админа и обычного пользователя
        self.normal_client.force_authenticate(user=self.normal_user)
        self.admin_client.force_authenticate(user=self.admin_user)

    def get_coupon_detail_url_with_kwargs(self, code):
        return reverse('coupons:coupons-detail', kwargs={'code': code})

    def check_coupon_data(self, coupon_data, coupon):
        self.assertEqual(coupon_data['code'], coupon.code)
        self.assertEqual(coupon_data['discount'], coupon.discount)
        self.assertEqual(coupon_data['valid_from'], coupon.valid_from)
        self.assertEqual(coupon_data['vailid_to'], coupon.vailid_to)
        self.assertEqual(coupon_data['is_active'], coupon.is_active)

    def test_anon_user_cannot_get_coupons_list(self):
        # Неправильная попытка получить список купонов анонимно и проверка
        invalid_anon_response = self.anon_client.get(self.list_coupons_url)
        self.assertEqual(invalid_anon_response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_normal_user_cannot_get_coupons_list(self):
        # Неправильная попытка получить список купонов обычыным пользователем и проверка
        invalid_normal_response = self.normal_client.get(self.list_coupons_url)
        self.assertEqual(invalid_normal_response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_user_can_get_coupons_list(self):
        # Получение списка купонов админом и проверка
        list_admin_response = self.admin_client.get(self.list_coupons_url)
        self.assertEqual(list_admin_response.status_code, status.HTTP_200_OK)
