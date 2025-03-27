from rest_framework import serializers
from .models import Payment


class PaymentSerializer(serializers.Serializer):
    total_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    email = serializers.EmailField()