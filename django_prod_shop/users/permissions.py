from typing import Any

from rest_framework.permissions import BasePermission, SAFE_METHODS
from rest_framework.request import Request


class ReadOnly(BasePermission):
    def has_permission(self, request: Request, view: Any) -> bool:
        return request.method in SAFE_METHODS
