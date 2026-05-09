from typing import Any

from rest_framework.request import Request
from rest_framework.permissions import BasePermission


class CanChangeProducts(BasePermission):
    def has_permission(self, request: Request, view: Any) -> bool:
        return request.user.is_authenticated and request.user.has_perm('products.manage_products')


class CanChangeCategories(BasePermission):
    def has_permission(self, request: Request, view: Any) -> bool:
        return request.user.is_authenticated and request.user.has_perm('products.manage_categories')
