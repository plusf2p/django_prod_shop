from rest_framework.permissions import BasePermission


class CanChangeCoupons(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.has_perm('coupons.manage_coupons')
