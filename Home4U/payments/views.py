from asyncio import log
from django.http import HttpResponse
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
from rest_framework.permissions import IsAuthenticated
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
import json
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



"""
Testing
"""

# class InitiatePayment(APIView):

#     permission_classes = [IsAuthenticated]

#     def post(self, request, reservation_id):
#         """Process payment for a specific reservation"""
#         user = request.user
#         print(f"Reservation ID: {reservation_id}")
#         print(user)
#         reservation = ReservationDetails.objects.get(house=reservation_id, user=user)
#         print(f"Reservation ID: {reservation_id}")
#         print(f"Logged-in user: {user}")
#         total_amount = reservation.calculate_total_price()

#         if total_amount <= 0:
#             return Response({"error": "Invalid total price"}, status=status.HTTP_400_BAD_REQUEST)

#         email = user.email
#         reference = str(uuid.uuid4())

#         flutterwave_url = f"{settings.FLW_API_URL}/payments"
#         secret_key = settings.FLW_SECRET_KEY
#         vercel_url = getattr(settings, "VERCEL_APP_URL", None)

#         payload = {
#             "tx_ref": reference,
#             "amount": float(total_amount),
#             "currency": "NGN",
#             "redirect_url": f"{vercel_url}/payments/callback/",
#             "payment_type": "card",
#             "customer": {"email": email},
#         }

#         headers = {
#             "Authorization": f"Bearer {secret_key}",
#             "Content-Type": "application/json",
#         }

#         try:
#             payment = Payment.objects.create(
#                 user=user,
#                 reservation=reservation,
#                 total_amount=total_amount,
#                 reference=reference,
#                 status="pending",
#             )
#             response = requests.post(flutterwave_url, json=payload, headers=headers)
#             response_data = response.json()

#             if response.status_code == 200 and response_data.get("status") == "success":
#                 return Response(
#                     {
#                         "message": "Payment initiated successfully.",
#                         "payment_link": response_data["data"]["link"],
#                         "reference": reference,
#                     },
#                     status=status.HTTP_200_OK,
#                 )

#             return Response({"error": "Failed to initiate payment"}, status=status.HTTP_400_BAD_REQUEST)

#         except requests.exceptions.RequestException:
#             return Response({"error": "Payment initiation failed"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
#         except Exception as e:
#             return Response({"error": f"Database or unexpected error: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

"""
Original Testing
"""

class PaymentCallback(APIView):
    """Handles the redirect callback from Flutterwave"""

    def get(self, request):
        # tx_ref = request.GET.get('tx_ref')
        # url = f"https://api.flutterwave.com/v3/transactions/verify_by_reference?tx_ref={tx_ref}"
        # headers = {
        #     "Authorization": f"Bearer {settings.FLW_SECRET_KEY}",
        #     "Content-Type": "application/json"
        # }
        # response = requests.get(url, headers=headers)

        # if response.status_code != 200 or not response.text.strip():
        #     return Response({"error": "Invalid response from Flutterwave"}, status=400)

        # try:
        #     response_data = response.json()
        # except requests.exceptions.JSONDecodeError:
        #     return Response({"error": "Failed to decode Flutterwave response"}, status=500)
        
        reference = request.GET.get("reference")
        paystack_url_verify = f"{settings.PAYSTACK_URL_VERIFY}/{reference}"
        paystack_secret_key = f"{settings.PAYSTACK_SECRET_KEY}"
        reference = request.GET.get("reference")
        headers_paystack ={
            "Authorization": f"Bearer {paystack_secret_key}",
            "Content-Type": "application/json"
        }
        response_paystack_get = requests.get(paystack_url_verify, headers=headers_paystack)
        res_data = response_paystack_get.json()

        if res_data["data"]["status"] == "success":
            # Update payment status in DB here
            payment = Payment.objects.get(reference=reference)
            payment.status = Payment.Status.SUCCESSFUL
            payment.save()
            return Response({"message": "Payment successful"}, status=200)

        return Response({"error": "Payment failed"}, status=400)
    
        # if response_data['data']['status'] == "successful":
        #     try:
        #         payment = Payment.objects.get(reference=tx_ref)
        #         payment.status = Payment.Status.SUCCESSFUL
        #         payment.save()
        #         total = payment.total_amount
        #         user = payment.user
        #         first_name = user.first_name
        #         last_name = user.last_name
        #         email = user.email
        #         check_in = payment.reservations.check_in
        #         check_out = payment.reservations.check_out
        #         guest = payment.reservations.guests
        #         house = payment.housenames.house
        #         booking = tx_ref
        #         print(f'tx_ref: {tx_ref}')
                
        #         print(f"email: {email}")
        #         full_name = f"{first_name} {last_name}"
        #         print(f"fullname: {full_name}")
                
        #         return Response({"message": "Payment was successful",
        #                          "name": full_name,
        #                          "email": email,
        #                          "total":total,
        #                          "check_in":check_in,
        #                          "guest":guest,
        #                          "check_out":check_out,
        #                          "house":house,
        #                          "booking":booking}, status=200)
                
        #     except Payment.DoesNotExist:
        #         return Response({"error": "Payment not found"}, status=404)

        # return Response({"error": "Payment failed"}, status=400)

    

@method_decorator(csrf_exempt, name='dispatch')
class WebhookCallback(APIView):
    """
    Handles Flutterwave Webhook Events (validated)
    """

    def post(self, request):
        # ✅ Get raw payload
        payload = request.body

        # ✅ Get Flutterwave signature and compare with your secret hash
        signature = request.headers.get('verif-hash')
        secret_hash = settings.FLW_SECRET_HASH

        if not signature or signature != secret_hash:
            return HttpResponse("Invalid signature", status=401)

        # ✅ Try parsing the incoming JSON payload
        try:
            event = json.loads(payload)
        except ValueError:
            return HttpResponse("Invalid JSON", status=400)

        # ✅ Extract data
        data = event.get('data', {})
        tx_ref = data.get('tx_ref')  # 🛠️ Fixed here: get from parsed data, not request
        payment_status = data.get('status')

        # ✅ Check if payment is successful
        if payment_status == 'successful':
            # 🔍 Optional: re-verify with Flutterwave
            verify_url = f"https://api.flutterwave.com/v3/transactions/verify_by_reference?tx_ref={tx_ref}"
            headers = {
                "Authorization": f"Bearer {settings.FLW_SECRET_KEY}",
                "Content-Type": "application/json",
            }

            response = requests.get(verify_url, headers=headers)
            if response.status_code == 200:
                verify_data = response.json()
                payment_data = verify_data.get('data', {})

                if payment_data.get('status') == 'successful':
                    try:
                        payment = Payment.objects.get(reference=tx_ref)
                        payment.status = Payment.Status.SUCCESSFUL
                        payment.save()
                        return HttpResponse("Payment processed", status=200)
                    except Payment.DoesNotExist:
                        return HttpResponse("Payment not found", status=404)

        return HttpResponse("Webhook received", status=200)