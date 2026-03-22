from rest_framework.permissions import BasePermission


class IsManagerOrAdminOrOrAuthor(BasePermission):
    def has_object_permission(self, request, view, obj):
        user = request.user
        return user.is_authenticated and (user.has_perm('reviews.manage_reviews') or obj.user == user)


class IsManagerOrAdmin(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return user.is_authenticated and user.has_perm('reviews.manage_reviews')
