from typing import Any
import logging

from drf_spectacular.utils import extend_schema
from drf_spectacular.types import OpenApiTypes

from rest_framework.mixins import RetrieveModelMixin, UpdateModelMixin
from rest_framework.throttling import ScopedRateThrottle, BaseThrottle
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import GenericViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.request import Request
from rest_framework import status

from rest_framework_simplejwt.views import TokenObtainPairView

from django.db.models import QuerySet
from djoser.views import UserViewSet

from django_prod_shop.cart.services import merge_cart
from django_prod_shop.users.models import Profile
from .serializers import ProfileSerializer, MyTokenObtainPairSerializer


logger = logging.getLogger(__name__)


class MyTokenObtainPairView(TokenObtainPairView):
    serializer_class = MyTokenObtainPairSerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'login'

    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            merge_cart(request, user=serializer.user)
        except Exception:
            logger.exception('Слияние корзин при логине провалилось')

        return Response(serializer.validated_data, status=status.HTTP_200_OK)


class ProfileViewSet(RetrieveModelMixin, UpdateModelMixin, GenericViewSet):
    queryset = Profile.objects.all()
    serializer_class = ProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self) -> QuerySet[Profile]:
        qs = super().get_queryset()
        user = self.request.user

        if (self.action in ['retrieve', 'update', 'partial_update']) and not user.has_perm('users.manage_profiles'):
            qs = qs.filter(user=user)
        
        return qs

    @extend_schema(
        tags=['profile'],
        summary='Получить/изменить страницу профиля пользователя',
        description=(
            'Получение или изменение страницы профиля пользователя.'
        ),
        request=ProfileSerializer,
        responses={
            status.HTTP_200_OK: ProfileSerializer,
        },
    )
    @action(detail=False, methods=['get', 'patch'], url_path='me')
    def me(self, request: Request) -> Response:
        profile, _ = Profile.objects.get_or_create(user=request.user)

        if request.method == 'PATCH':
            serializer = self.get_serializer(profile, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()

            return Response(serializer.data, status=status.HTTP_200_OK)
        
        serializer = self.get_serializer(profile)
        return Response(serializer.data, status=status.HTTP_200_OK)


class MyUserViewSet(UserViewSet):
    throttle_classes = [ScopedRateThrottle]

    def get_throttles(self) -> list[BaseThrottle]:
        if self.action == 'create':
            self.throttle_scope = 'register'
        elif self.action == 'reset_password':
            self.throttle_scope = 'reset_password'
        elif self.action == 'reset_password_confirm':
            self.throttle_scope = 'reset_password_confirm'
        elif self.action == 'set_password':
            self.throttle_scope = 'set_password'
        else:
            return []

        return super().get_throttles()
