from typing import Any

from rest_framework.permissions import BasePermission
from rest_framework.request import Request


class CanChangeOrders(BasePermission):
    def has_permission(self, request: Request, view: Any) -> bool:
        return request.user.is_authenticated and request.user.has_perm('orders.manage_orders')
