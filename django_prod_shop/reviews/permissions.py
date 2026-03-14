from rest_framework.permissions import BasePermission


from django_prod_shop.reviews.models import Review
from django_prod_shop.orders.models import Order


class IsAdminOrAuthor(BasePermission):
    def has_permission(self, request, view, obj):
        return request.user.is_staff or obj.user == request.user


class IsAdminOrBuyer(BasePermission):
    def has_permission(self, request, view, obj):
        if Review.objects.filter(pk=obj.pk, user=request.user):
            return False
        
        is_buyer = Order.objects.filter(user=request.user, status=Order.StatusChoices.DELIVERED).exists()
        return request.user.is_staff or is_buyer
