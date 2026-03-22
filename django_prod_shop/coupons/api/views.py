from rest_framework.viewsets import ModelViewSet

from django_prod_shop.coupons.permissions import CanChangeCoupons
from django_prod_shop.coupons.models import Coupon
from .serializers import CouponSerializer


class CouponsViewSet(ModelViewSet):
    serializer_class = CouponSerializer
    queryset = Coupon.objects.all()
    permission_classes = [CanChangeCoupons]
    lookup_field = 'code'
