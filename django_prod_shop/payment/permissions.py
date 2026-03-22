from rest_framework.permissions import BasePermission


class CanChangePament(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.has_perm('payment.manage_payments')
