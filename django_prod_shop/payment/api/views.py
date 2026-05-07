from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from django.urls import reverse

from rest_framework.viewsets import GenericViewSet
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.decorators import action, api_view, permission_classes, authentication_classes
from rest_framework.response import Response
from rest_framework import status

from django_prod_shop.payment.permissions import CanChangePayment
from django_prod_shop.payment.models import Payment
from django_prod_shop.payment.services import create_payment_service
from .serializers import PaymentSerializer


class PaymentViewSet(ListModelMixin, RetrieveModelMixin, GenericViewSet):
    queryset = Payment.objects.select_related('order', 'order__user')
    serializer_class = PaymentSerializer
    lookup_field = 'payment_id'

    def get_queryset(self):
        qs = super().get_queryset()

        if self.request.user.has_perm('payment.manage_payments'):
            return qs
        
        return qs.filter(order__user=self.request.user)

    def get_permissions(self):
        if self.action in ['create_payment', 'retrieve']:
            permission_classes = [IsAuthenticated]
        else:
            permission_classes = [CanChangePayment]
        
        return [permission() for permission in permission_classes]

    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
    
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        tags=['payment'],
        summary='Создать платеж',
        description=(
            'Создание платежа. Принимает order_id. '
            'При неверных order_id возвращает ошибки 400/403/404.'
        ),
        parameters=[
            OpenApiParameter(
                name='order_id',
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.PATH,
                description='ID заказа',
                required=True,
            ),
        ],
        request=None,
        responses={
            status.HTTP_201_CREATED: OpenApiTypes.OBJECT,
            status.HTTP_400_BAD_REQUEST: OpenApiTypes.OBJECT,
            status.HTTP_403_FORBIDDEN: OpenApiTypes.OBJECT,
            status.HTTP_404_NOT_FOUND: OpenApiTypes.OBJECT,
        },
        examples=[
            OpenApiExample(
                name='Создание платежа',
                value={
                    'id': 5, 
                    'payment_id': '2f1b3c4d-000f-5b99-90a0-1a2b3c4b5e6f',
                    'confirmation_url': '/some-confirmation-url/'
                },
                response_only=True,
                status_codes=['201'],
            ),
            OpenApiExample(
                name='Нет email у пользователя',
                value={
                    'email': 'У вас не указан email', 
                },
                response_only=True,
                status_codes=['400'],
            ),
            OpenApiExample(
                name='Попытка оплатить чужой заказ',
                value={
                    'error': 'Вы не можете оплачивать чужой заказ', 
                },
                response_only=True,
                status_codes=['403'],
            ),
            OpenApiExample(
                name='Попытка оплатить заказ с существующим платежом',
                value={
                    'error': 'У этого заказа уже есть платеж', 
                },
                response_only=True,
                status_codes=['400'],
            ),
            OpenApiExample(
                name='Платеж уже завершен',
                value={
                    'error': 'Оплата для этого заказа недоступна', 
                },
                response_only=True,
                status_codes=['400'],
            ),
            OpenApiExample(
                name='Заказа не существует',
                value={
                    'error': 'Такого заказа не существует', 
                },
                response_only=True,
                status_codes=['404'],
            ),
            OpenApiExample(
                name='Ошибка при создании платежа',
                value={
                    'error': 'Не удалось создать платёж. Попробуйте ещё раз', 
                },
                response_only=True,
                status_codes=['400'],
            ),
        ]
    )
    @action(detail=False, methods=['post'], url_path=r'create/(?P<order_id>[^/.]+)', url_name='create')
    def create_payment(self, request, order_id=None):
        return create_payment_service(request, order_id)


@extend_schema(
    tags=['payment'],
    summary='Страница после завершения платежа',
    description='Получает ссылку для редиректа после завершения платежа.',
    request=None,
    responses={
        status.HTTP_200_OK: OpenApiTypes.OBJECT,
    },
    examples=[
        OpenApiExample(
            name='Завершение платежа',
            value={
                'payment_status': 'completed', 
                'redirect_url': '/some-redirect-url/',
            },
            response_only=True,
            status_codes=['200'],
        )
    ]
)
@api_view(['GET'])
@permission_classes([AllowAny])
@authentication_classes([])
def payment_completed(request):
    return Response({
        'payment_status': 'completed', 
        'redirect_url': request.build_absolute_uri(reverse('orders:orders-list')),
    }, status=status.HTTP_200_OK)
