from rest_framework.permissions import BasePermission


class CanChangeProducts(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.has_perm('products.manage_catalog')


class CanChangeCategories(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.has_perm('category.manage_catalog')
