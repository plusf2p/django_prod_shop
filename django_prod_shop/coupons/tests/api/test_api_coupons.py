from datetime import timedelta, datetime
from uuid import uuid4

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

    #def get_list_of_codes(self, coupon_response):
    #    return {item['code'] for item in coupon_response.data}

    def get_item_in_list(self, coupon_response, code):
        for item in coupon_response.data:
            if item['code'] == code:
                return item
        self.fail(f"Купон '{code}' не найден в ответе")

    def check_coupon_in_coupon_data(self, coupon_data, coupon):
        self.assertEqual(coupon_data['code'], coupon.code)
        self.assertEqual(coupon_data['discount'], coupon.discount)
        
        self.assertEqual(
            coupon_data['valid_from'],
            self.bring_date_to_correct_form(coupon.valid_from),
        )
        self.assertEqual(
            coupon_data['valid_to'],
            self.bring_date_to_correct_form(coupon.valid_to),
        )
        self.assertEqual(coupon_data['is_active'], coupon.is_active)
    
    def check_coupon_from_db(self, code, **data):
        self.assertTrue(Coupon.objects.filter(code=code).exists())
        coupon = Coupon.objects.get(code=code)
        self.assertEqual(coupon.code, code)

        for key, value in data.items():
            self.assertEqual(getattr(coupon, key), value)
        
        return coupon

    def bring_date_to_correct_form(self, date):
        return date.strftime("%Y-%m-%d")

    def update_coupon_data(self, **new_data):
        time_start = timezone.now().date()
        time_end = (timezone.now() + timedelta(days=7)).date()
        data = {
            'code': f'test-{uuid4().hex[:8]}',
            'valid_from': time_start,
            'valid_to': time_end,
            'discount': 50,
            'is_active': True,
        }
        data.update(new_data)
        return data

    def test_anon_user_cannot_get_coupons_list(self):
        # Неправильная попытка получить список купонов анонимно и проверка
        invalid_anon_response = self.anon_client.get(self.list_coupons_url)
        self.assertEqual(invalid_anon_response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_normal_user_cannot_get_coupons_list(self):
        # Неправильная попытка получить список купонов обычыным пользователем и проверка
        invalid_normal_response = self.normal_client.get(self.list_coupons_url)
        self.assertEqual(invalid_normal_response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_user_can_get_list_of_normal_and_inactive_coupons(self):
        # Получение списка купонов админом и проверка
        list_admin_response = self.admin_client.get(self.list_coupons_url)
        self.assertEqual(list_admin_response.status_code, status.HTTP_200_OK)

        # Получение и проверка первого правильного купона
        coupon1_data = self.get_item_in_list(
            coupon_response=list_admin_response, code=self.coupon1.code,
        )
        self.check_coupon_in_coupon_data(coupon_data=coupon1_data, coupon=self.coupon1)

        # Получение и проверка второго правильного купона
        coupon2_data = self.get_item_in_list(
            coupon_response=list_admin_response, code=self.coupon2.code,
        )
        self.check_coupon_in_coupon_data(coupon_data=coupon2_data, coupon=self.coupon2)

        # Получение и проверка неактивного купона
        coupon_inactive_data = self.get_item_in_list(
            coupon_response=list_admin_response, code=self.coupon_inactive.code,
        )
        self.check_coupon_in_coupon_data(coupon_data=coupon_inactive_data, coupon=self.coupon_inactive)

        # Получение и проверка первого непарвильного купона
        coupon_past_data = self.get_item_in_list(
            coupon_response=list_admin_response, code=self.coupon_past.code,
        )
        self.check_coupon_in_coupon_data(coupon_data=coupon_past_data, coupon=self.coupon_past)

        # Получение и проверка второго непарвильного купона
        coupon_future_data = self.get_item_in_list(
            coupon_response=list_admin_response, code=self.coupon_future.code,
        )
        self.check_coupon_in_coupon_data(coupon_data=coupon_future_data, coupon=self.coupon_future)

    def test_anon_user_cannot_get_coupon_detail(self):
        # Неправильная попытка получить купон анонимно и проверка
        invalid_anon_response = self.anon_client.get(
            self.get_coupon_detail_url_with_kwargs(code=self.coupon1.code),
        )
        self.assertEqual(invalid_anon_response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_normal_user_cannot_get_coupon_detail(self):
        # Неправильная попытка получить купон обычыным пользователем и проверка
        invalid_normal_response = self.normal_client.get(
            self.get_coupon_detail_url_with_kwargs(code=self.coupon1.code),
        )
        self.assertEqual(invalid_normal_response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_user_can_get_any_coupon_detail(self):
        # Получение обычного купона админом и проверка
        detail_admin_response = self.admin_client.get(
            self.get_coupon_detail_url_with_kwargs(code=self.coupon1.code),
        )
        self.assertEqual(detail_admin_response.status_code, status.HTTP_200_OK)
        self.check_coupon_in_coupon_data(coupon_data=detail_admin_response.data, coupon=self.coupon1)

         # Получение неактивного купона админом и проверка
        inactive_detail_admin_response = self.admin_client.get(
            self.get_coupon_detail_url_with_kwargs(code=self.coupon_inactive.code),
        )
        self.assertEqual(inactive_detail_admin_response.status_code, status.HTTP_200_OK)
        self.check_coupon_in_coupon_data(coupon_data=inactive_detail_admin_response.data, coupon=self.coupon_inactive)

         # Получение первого неправильного купона админом и проверка
        past_detail_admin_response = self.admin_client.get(
            self.get_coupon_detail_url_with_kwargs(code=self.coupon_past.code),
        )
        self.assertEqual(past_detail_admin_response.status_code, status.HTTP_200_OK)
        self.check_coupon_in_coupon_data(coupon_data=past_detail_admin_response.data, coupon=self.coupon_past)

         # Получение второго неправильного купона админом и проверка
        future_detail_admin_response = self.admin_client.get(
            self.get_coupon_detail_url_with_kwargs(code=self.coupon_future.code),
        )
        self.assertEqual(future_detail_admin_response.status_code, status.HTTP_200_OK)
        self.check_coupon_in_coupon_data(coupon_data=future_detail_admin_response.data, coupon=self.coupon_future)

    def test_anon_user_cannot_create_coupon(self):
        # Данные для создания купона
        test_coupon_data = self.update_coupon_data()

        # Неправильная попытка создать купон анонимно и проверка
        invalid_anon_response = self.anon_client.post(
            self.list_coupons_url, data=test_coupon_data,
        )
        self.assertEqual(invalid_anon_response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_normal_user_create_delete_coupon(self):
        # Данные для создания купона
        test_coupon_data = self.update_coupon_data()

        # Неправильная попытка создать купон обычным пользователем и проверка
        invalid_normal_response = self.normal_client.post(
            self.list_coupons_url, data=test_coupon_data,
        )
        self.assertEqual(invalid_normal_response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_user_cannot_create_coupon_with_invalid_code(self):
        # Правильное время для купонов
        time_start = timezone.now().date()
        time_end = (timezone.now() + timedelta(days=7)).date()

        # Неправильные данные для создания купона
        invalid_test_coupon_data = {
            'valid_from': self.bring_date_to_correct_form(time_start),
            'valid_to': self.bring_date_to_correct_form(time_end),
            'discount': 50,
            'is_active': True,
        }

        # Неправльное создание купона админом и проверка
        invalid_admin_response = self.admin_client.post(
            self.list_coupons_url, data=invalid_test_coupon_data,
        )
        self.assertEqual(invalid_admin_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertNotIn('valid_from', invalid_admin_response.data)
        self.assertNotIn('valid_to', invalid_admin_response.data)
        self.assertIn('code', invalid_admin_response.data)

    def test_admin_user_cannot_create_coupon_with_invalid_date_from(self):
        # Правильное время для купонов
        time_start = (timezone.now() + timedelta(days=7)).date()
        time_end = timezone.now().date()

        # Неправильные данные для создания купона
        invalid_test_coupon_data = {
            'code': 'test-coupon-with-invalid-date',
            'valid_from': self.bring_date_to_correct_form(time_start),
            'valid_to': self.bring_date_to_correct_form(time_end),
            'discount': 50,
            'is_active': True,
        }

        # Неправльное создание купона админом и проверка
        invalid_admin_response = self.admin_client.post(
            self.list_coupons_url, data=invalid_test_coupon_data,
        )
        self.assertEqual(invalid_admin_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertNotIn('code', invalid_admin_response.data)
        self.assertNotIn('valid_to', invalid_admin_response.data)
        self.assertIn('valid_from', invalid_admin_response.data)

    def test_admin_user_cannot_create_coupon_with_invalid_date_to(self):
        # Правильное время для купонов
        time_start = timezone.now().date()
        time_end = (timezone.now() - timedelta(days=7)).date()

        # Неправильные данные для создания купона
        invalid_test_coupon_data = {
            'code': 'test-coupon-with-invalid-date',
            'valid_from': self.bring_date_to_correct_form(time_start),
            'valid_to': self.bring_date_to_correct_form(time_end),
            'discount': 50,
            'is_active': True,
        }

        # Неправльное создание купона админом и проверка
        invalid_admin_response = self.admin_client.post(
            self.list_coupons_url, data=invalid_test_coupon_data,
        )
        self.assertEqual(invalid_admin_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertNotIn('code', invalid_admin_response.data)
        self.assertNotIn('valid_from', invalid_admin_response.data)
        self.assertIn('valid_to', invalid_admin_response.data)

    def test_admin_user_can_create_coupon(self):
        # Данные для создания купона
        test_coupon_data = self.update_coupon_data()

        # Создание купона админом и проверка
        admin_response = self.admin_client.post(
            self.list_coupons_url, data=test_coupon_data,
        )
        self.assertEqual(admin_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(admin_response.data['code'], test_coupon_data['code'])
        self.assertEqual(
            admin_response.data['valid_from'], 
            self.bring_date_to_correct_form(test_coupon_data['valid_from']),
        )
        self.assertEqual(
            admin_response.data['valid_to'], 
            self.bring_date_to_correct_form(test_coupon_data['valid_to']),
        )
        self.assertEqual(admin_response.data['discount'], test_coupon_data['discount'])
        self.assertEqual(admin_response.data['is_active'], test_coupon_data['is_active'])

        # Проверка нового купона
        new_coupon = self.check_coupon_from_db(
            code=test_coupon_data['code'],
            valid_from=test_coupon_data['valid_from'],
            valid_to=test_coupon_data['valid_to'],
            discount=test_coupon_data['discount'],
            is_active=test_coupon_data['is_active'],
        )

        # Получение нового купона и проверка
        admin_detail_response = self.admin_client.get(
            self.get_coupon_detail_url_with_kwargs(code=test_coupon_data['code']),
        )
        self.assertEqual(admin_detail_response.status_code, status.HTTP_200_OK)
        self.check_coupon_in_coupon_data(coupon_data=admin_detail_response.data, coupon=new_coupon)

    def test_anon_user_cannot_delete_coupon(self):
        # Неправильная попытка удалить купон анонимно и проверка
        invalid_anon_response = self.anon_client.delete(
            self.get_coupon_detail_url_with_kwargs(code=self.coupon1.code),
        )
        self.assertEqual(invalid_anon_response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_normal_user_cannot_delete_coupon(self):
        # Неправильная попытка удалить купон обычыным пользователем и проверка
        invalid_normal_response = self.normal_client.delete(
            self.get_coupon_detail_url_with_kwargs(code=self.coupon1.code),
        )
        self.assertEqual(invalid_normal_response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_user_can_delete_coupon(self):
        # Удаление обычного купона админом и проверка
        delete_admin_response = self.admin_client.delete(
            self.get_coupon_detail_url_with_kwargs(code=self.coupon1.code),
        )
        self.assertEqual(delete_admin_response.status_code, status.HTTP_204_NO_CONTENT)

        # Попытка получить удаленный купон и проверка
        delete_admin_response = self.admin_client.get(
            self.get_coupon_detail_url_with_kwargs(code=self.coupon1.code),
        )
        self.assertEqual(delete_admin_response.status_code, status.HTTP_404_NOT_FOUND)
