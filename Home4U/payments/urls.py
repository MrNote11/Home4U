from django.urls import path
from .views import InitiatePayment, PaymentCallback#BankTransferView

urlpatterns = [
    path("initiate-payment/<int:reservation_id>/", InitiatePayment.as_view(), name="initiate-payment"),
    path("confirmation/", PaymentCallback.as_view(), name="payment-callback"),
    # path("transfers/initiate/", BankTransferView.as_view(), name="initiate-transfer"),
]
