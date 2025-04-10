from django.urls import path
from .views import (InitiatePayment, PaymentCallback,
                    WebhookCallback)

urlpatterns = [
    path("initiate-payment/<int:reservation_id>/", InitiatePayment.as_view(), name="initiate-payment"),
    path("confirmation/", PaymentCallback.as_view(), name="payment-callback"),
    path('webhook/flutterwave/', WebhookCallback.as_view(), name='flutterwave-webhook')
    # path("transfers/initiate/", BankTransferView.as_view(), name="initiate-transfer"),
]
