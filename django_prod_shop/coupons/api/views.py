from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAdminUser

from django_prod_shop.coupons.models import Coupon
from .serializers import CouponSerializer


class CouponsViewSet(ModelViewSet):
    serializer_class = CouponSerializer
    queryset = Coupon.objects.all()
    permission_classes = [IsAdminUser]
    lookup_field = 'code'
