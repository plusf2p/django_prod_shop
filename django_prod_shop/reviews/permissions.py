from typing import Any

from rest_framework.permissions import BasePermission
from rest_framework.request import Request

from .models import Review


class IsManagerOrAdminOrAuthor(BasePermission):
    def has_object_permission(self, request: Request, view: Any, obj: Review) -> bool:
        user = request.user
        return user.is_authenticated and (user.has_perm('reviews.manage_reviews') or obj.user == user)


class IsManagerOrAdmin(BasePermission):
    def has_permission(self, request: Request, view: Any) -> bool:
        user = request.user
        return user.is_authenticated and user.has_perm('reviews.manage_reviews')
