from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
import requests
import uuid
from rest_framework import status
from django.conf import settings
from .models import Payment
from .utils import get_bank_code, resolve_account
from django.shortcuts import get_object_or_404
from .models import Payment, ReservationDetails


class BankTransferView(APIView):
    def post(self, request):
        """Handles bank transfers using Flutterwave"""
        data = request.data
        country = data.get("country", "NG")
        account_number = data.get("account_number")
        account_bank = data.get("account_bank")
        amount = data.get("amount")
        narration = data.get("narration", "Payment for services rendered")
        currency = data.get("currency", "NGN")
        reference = str(uuid.uuid4())

        # Step 1: Get Bank Code
        selected_bank = get_bank_code(country, account_bank)

        # Step 2: Resolve Account
        account_details = resolve_account(account_number, selected_bank["code"])

        # Step 3: Initiate Transfer
        url = "https://api.flutterwave.com/v3/transfers"
        headers = {
            "Authorization": f"Bearer {settings.FLW_SECRET_KEY}",
            "Content-Type": "application/json"
        }
        transfer_data = {
            "account_bank": selected_bank["code"],
            "account_number": account_number,
            "amount": amount,
            "narration": narration,
            "currency": currency,
            "reference": reference,
            "callback_url": f"{settings.VERCEL_APP_URL}/callback"
        }

        response = requests.post(url, headers=headers, json=transfer_data)
        if response.status_code != 200:
            return Response({"error": "Transfer failed"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(response.json(), status=status.HTTP_200_OK)




class InitiatePayment(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request, reservation_id):
        """Process payment for a specific reservation"""
        user = request.user
        print(f"Reservation ID: {reservation_id}")
        print(user)
        reservation = ReservationDetails.objects.get(post_id=reservation_id, user=user)
        print(f"Reservation ID: {reservation_id}")
        print(f"Logged-in user: {user}")
        total_amount = reservation.calculate_total_price()

        if total_amount <= 0:
            return Response({"error": "Invalid total price"}, status=status.HTTP_400_BAD_REQUEST)

        email = user.email
        reference = str(uuid.uuid4())

        flutterwave_url = f"{settings.FLW_API_URL}/payments"
        secret_key = settings.FLW_SECRET_KEY
        vercel_url = getattr(settings, "VERCEL_APP_URL", None)

        payload = {
            "tx_ref": reference,
            "amount": float(total_amount),
            "currency": "NGN",
            "redirect_url": f"{vercel_url}/payments/callback/",
            "payment_type": "card",
            "customer": {"email": email},
        }

        headers = {
            "Authorization": f"Bearer {secret_key}",
            "Content-Type": "application/json",
        }

        try:
            payment = Payment.objects.create(
                user=user,
                reservation=reservation,
                total_amount=total_amount,
                reference=reference,
                status="pending",
            )
            response = requests.post(flutterwave_url, json=payload, headers=headers)
            response_data = response.json()

            if response.status_code == 200 and response_data.get("status") == "success":
                return Response(
                    {
                        "message": "Payment initiated successfully.",
                        "payment_link": response_data["data"]["link"],
                        "reference": reference,
                    },
                    status=status.HTTP_200_OK,
                )

            return Response({"error": "Failed to initiate payment"}, status=status.HTTP_400_BAD_REQUEST)

        except requests.exceptions.RequestException:
            return Response({"error": "Payment initiation failed"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            return Response({"error": f"Database or unexpected error: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



class PaymentCallback(APIView):
    """Handles the payment callback from Flutterwave"""

    def get(self, request):
        status_param = request.GET.get('status')
        tx_ref = request.GET.get('tx_ref')
        
        print(f"1:{tx_ref}")
        # Construct the verification URL
        url = f"https://api.flutterwave.com/v3/transactions/verify_by_reference?tx_ref={tx_ref}"
        print(f"2:{tx_ref}")
        headers = {
            "Authorization": f"Bearer {settings.FLW_SECRET_KEY}",
            "Content-Type": "application/json"
        }
        print(f"FLK{settings.FLW_SECRET_KEY}")

        # Make request to Flutterwave
        response = requests.get(url, headers=headers)
        print(f"3:{tx_ref}")
        # **Fix: Check if the response is empty**
        print(f"4:status {response}")
        if response.status_code != 200 or not response.text.strip():
            return Response(
                {"error": "Invalid response from Flutterwave"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            response_data = response.json()
        except requests.exceptions.JSONDecodeError:
            return Response(
                {"error": "Failed to decode Flutterwave response"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # Process payment
        
        print(f"5{response_data}")
        if response_data['data']['status'] == "successful":
            try:
                payment = Payment.objects.get(reference=tx_ref)
                print(f"payment: {payment}")
                payment.status = "successful"
                payment.save()
                return Response({"message": "Payment was successful"}, status=status.HTTP_200_OK)
            except Payment.DoesNotExist:
                return Response({"error": "Payment not found"}, status=status.HTTP_404_NOT_FOUND)

        return Response({"error": "Payment failed"}, status=status.HTTP_400_BAD_REQUEST)