import logging

from rest_framework import status
from rest_framework.mixins import RetrieveModelMixin, UpdateModelMixin
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.throttling import ScopedRateThrottle

from rest_framework_simplejwt.views import TokenObtainPairView

from djoser.views import UserViewSet

from django_prod_shop.cart.services import merge_cart
from django_prod_shop.users.models import Profile
from .serializers import ProfileSerializer, MyTokenObtainPairSerializer


logger = logging.getLogger(__name__)


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


class ProfileViewSet(RetrieveModelMixin, UpdateModelMixin, GenericViewSet):
    queryset = Profile.objects.all()
    serializer_class = ProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user

        if (self.action in ['retrieve', 'update', 'partial_update']) and not user.has_perm('users.manage_profiles'):
            qs = qs.filter(user=user)
        
        return qs


class MyUserViewSet(UserViewSet):
    throttle_classes = [ScopedRateThrottle]

    def get_throttles(self):
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
