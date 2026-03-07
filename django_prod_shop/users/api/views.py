from collections.abc import Sequence
from typing import Any

from django.db.models.query import QuerySet
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.mixins import (ListModelMixin, RetrieveModelMixin, UpdateModelMixin, 
                                   CreateModelMixin)
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.serializers import BaseSerializer
from rest_framework.viewsets import GenericViewSet
from rest_framework.permissions import _SupportsHasPermission, IsAuthenticated, AllowAny

from django_prod_shop.users.models import User, Profile

from .serializers import UserSerializer, ProfileSerializer, RegisterProfileSerializer


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


class RegisterViewSet(CreateModelMixin, GenericViewSet):
    queryset = Profile.objects.select_related('user')
    serializer_class = RegisterProfileSerializer
    permission_classes = [AllowAny]


class ProfileViewSet(RetrieveModelMixin, UpdateModelMixin, GenericViewSet):
    queryset = Profile.objects.all()
    serializer_class = ProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        
        if self.action in ['retrieve', 'update', 'partial_update'] and not user.is_staff:
            qs = qs.filter(user=user)
        
        return qs
