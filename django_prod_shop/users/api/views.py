import logging

from django.db import transaction

from rest_framework import status
from rest_framework.decorators import action
from rest_framework.mixins import (ListModelMixin, RetrieveModelMixin, UpdateModelMixin, 
                                   CreateModelMixin)
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.throttling import ScopedRateThrottle

from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken

from django_prod_shop.cart.services import merge_cart
from django_prod_shop.users.models import User, Profile
from django_prod_shop.users.tasks import send_reset_password_email
from .serializers import (UserSerializer, ProfileSerializer, RegisterProfileSerializer, 
                          MyTokenObtainPairSerializer, ChangePasswordSerializer,
                          PasswordResetSerializer)


logger = logging.getLogger(__name__)


class UserViewSet(RetrieveModelMixin, ListModelMixin, UpdateModelMixin, GenericViewSet):
    serializer_class = UserSerializer
    queryset = User.objects.all()
    lookup_field = "pk"

    def get_queryset(self, *args, **kwargs):
        assert isinstance(self.request.user.id, int)
        return self.queryset.filter(id=self.request.user.id)

    @action(detail=False)
    def me(self, request):
        serializer = UserSerializer(request.user, context={"request": request})
        return Response(status=status.HTTP_200_OK, data=serializer.data)


class MyTokenObtainPairView(TokenObtainPairView):
    serializer_class = MyTokenObtainPairSerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'login'

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            merge_cart(request, user=serializer.user)
        except Exception:
            logger.exception('Слияние корзин при логине провалилось')

        return Response(serializer.validated_data, status=status.HTTP_200_OK)


class RegisterViewSet(CreateModelMixin, GenericViewSet):
    queryset = Profile.objects.select_related('user')
    serializer_class = RegisterProfileSerializer
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'register'


class ProfileViewSet(RetrieveModelMixin, UpdateModelMixin, GenericViewSet):
    queryset = Profile.objects.all()
    serializer_class = ProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user

        if (self.action in ['retrieve', 'update', 'partial_update']) and not user.has_perm('manage_profiles'):
            qs = qs.filter(user=user)
        
        return qs


class ChangePasswordAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request, *args, **kwargs):
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        new_password = serializer.validated_data['new_password1']
        
        request.user.set_password(new_password)
        request.user.save()
        refresh = RefreshToken.for_user(request.user)

        return Response({
            'password': 'Пароль успешно изменен',
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }, status=status.HTTP_200_OK)


class PasswordResetAPIView(APIView):
    permission_classes = [AllowAny]
    scope = 'password_reset'
    
    def post(self, request, *args, **kwargs):
        serializer = PasswordResetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']
        
        transaction.on_commit(lambda: send_reset_password_email.delay(email=email, request=request))

        return Response({
            'detail': 'Инструкции по восстановлению пароля отправлены на ваш email. Провертье папку СПАМ'
        }, status=status.HTTP_200_OK)


class PasswordResetConfirmAPIView(APIView):
    permission_classes = [AllowAny]
    scope = 'password_reset_confirm'
    
    def post(self, request, *args, **kwargs):
        serializer = PasswordResetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']
        
        transaction.on_commit(lambda: send_reset_password_email.delay(email=email, request=request))

        return Response({
            'detail': 'Инструкции по восстановлению пароля отправлены на ваш email. Провертье папку СПАМ'
        }, status=status.HTTP_200_OK)
