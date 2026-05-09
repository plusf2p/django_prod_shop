from rest_framework import serializers

from django_prod_shop.orders.api.serializers import OrderReadSerializer
from django_prod_shop.payment.models import Payment


class PaymentSerializer(serializers.ModelSerializer):
    order = OrderReadSerializer(read_only=True)

    class Meta:
        model = Payment
        fields = ['order', 'amount', 'payment_id', 'status', 'created_at']
        read_only_fields = fields
