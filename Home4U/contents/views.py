
from .models import ReservationContents, PostRating, ReservationDetails, PostLike
from rest_framework import status, generics
from rest_framework.response import Response
from rest_framework import filters
from rest_framework.views import APIView
from .serializers import (ReservationContentsSerializer, GuestsSerializers, 
                          ReservationDetailSerializer, BookingSerializer,
                          PostLikeSerializer, PostRatingSerializer
                          )
from .paginations import Limits
from django_filters.rest_framework import DjangoFilterBackend
from .filters import ReservationFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import NotFound

from django.shortcuts import get_object_or_404
import uuid
from payments.models import Payment
from django.conf import settings
import requests
from django.db.models.functions import Round, Least
from django.db.models import Avg, Count, Value, FloatField, IntegerField, ExpressionWrapper, Func

from django.db.models import Avg, Count, Value, FloatField, ExpressionWrapper
from django.db.models.functions import Round, Least
from rest_framework import generics, status, filters
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
import calendar
from datetime import datetime, date, time



class HomeViews(generics.ListAPIView):
    serializer_class = ReservationContentsSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = Limits
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = ReservationFilter
    search_fields = ['house', 'state']

    def get_queryset(self):
        # Annotate extra fields for rating, likes, etc.
        queryset = ReservationContents.objects.annotate(
            raw_average_rating=Avg('ratings__ratings'),
            average_rating=Least(
                ExpressionWrapper(
                    Round(Avg('ratings__ratings')),
                    output_field=FloatField()  # Or IntegerField for rounded
                ),
                Value(5.0)
            ),
            total_raters=Count('ratings__user', distinct=True),
            total_likes=Count('post_likes')
        )

        query_params = self.request.query_params
        homepage_filter = query_params.get('homepage')

        # Filter according to the homepage parameter
        if homepage_filter == 'home':
            return queryset.order_by("-created")  # Changed to '-created' for latest first

        elif homepage_filter == 'newly added':
            return queryset.filter(status__icontains="Newly added")

        elif homepage_filter == 'ratings':
            return queryset.filter(status__icontains="Top Rated")

        # Return all if no filter specified
        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        if not queryset.exists():
            return Response({"message": "No results found."}, status=status.HTTP_404_NOT_FOUND)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)




class HomeDescriptions(generics.RetrieveAPIView):
     def get(self, request, pk):
        house = get_object_or_404(ReservationContents, id=pk)
        serializer = ReservationContentsSerializer(house)
        
        data={
            'posts': serializer.data
        }
        
        return Response(data)



class BookingViews(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user
        bookings = ReservationDetails.objects.filter(user=user)[:5]

        serializer = BookingSerializer(bookings, many=True)

        return Response({
            "data": serializer.data
        }, status=200)
        

class ReservationRatingView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request, post_pk, *args, **kwargs):
        user = request.user
        # Get the apartment
        apartment = get_object_or_404(ReservationContents, pk=post_pk)

        # Check if user has booked the apartment
        if not ReservationDetails.objects.filter(user=user, house=apartment).exists():
            return Response({"error": "You haven't booked this house."}, status=status.HTTP_400_BAD_REQUEST)

        # Validate rating
        serializer = PostRatingSerializer(data=request.data)
        if serializer.is_valid():
            rating = serializer.validated_data["ratings"]
            # Inside view
            # PostRating.objects.create(post=apartment, user=user, ratings=rating)


            # Save the rating
            PostRating.objects.create(post=apartment, user=user, ratings=rating)
            
            apartment_data = ReservationContentsSerializer(apartment).data
            return Response({
                "detail": apartment_data,
                "message": "Successfully rated"
            }, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)      
        
 
        
        
class LikePostView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request, pk):
        try:
            reservation = ReservationContents.objects.get(pk=pk)
        except ReservationContents.DoesNotExist:
            return Response({'error': 'Reservation not found'}, status=status.HTTP_404_NOT_FOUND)

        user = request.user
        like, created = PostLike.objects.get_or_create(post=reservation, user=user)

        total_likes = PostLike.objects.filter(post=reservation).count()  # ✅ Get updated like count

        if not created:
            return Response({'message': 'Reservation already liked', 'likes_count': total_likes}, status=status.HTTP_200_OK)

        return Response({'message': 'Reservation liked', 'likes_count': total_likes}, status=status.HTTP_201_CREATED)





class UnlikePostView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        try:
            reservation = ReservationContents.objects.get(pk=pk)
        except ReservationContents.DoesNotExist:
            return Response({'error': 'Reservation not found'}, status=status.HTTP_404_NOT_FOUND)

        user = request.user

        like = PostLike.objects.filter(post=reservation, user=user).first()
        if not like:
            return Response({'message': 'Reservation not liked yet'}, status=status.HTTP_400_BAD_REQUEST)

        like.delete()
        
        total_likes = PostLike.objects.filter(post=reservation).count()  # ✅ Get updated like count
        
        return Response({'message': 'Reservation unliked', 'likes_count': total_likes}, status=status.HTTP_200_OK)


class UserLikedPostsView(generics.ListAPIView):
    serializer_class = PostLikeSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return PostLike.objects.filter(user=user)


# New Housing Contents View (Latest Posts)
class NewHousingContentsViewList(generics.ListAPIView):
    queryset = ReservationContents.objects.all().order_by('-created')
    serializer_class = ReservationContentsSerializer
    permission_classes = [IsAuthenticated]

new_post = NewHousingContentsViewList.as_view()





class CreateGuests(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = GuestsSerializers
    
    def post(self, request, post_pk):
        user = request.user
        
        try:
            house = get_object_or_404(ReservationContents, id=post_pk)
            
            # Check if the user already has an active booking for this house
            active_booking = ReservationDetails.objects.filter(
                house=house,
                user=user,
                booking=True,  # Only consider confirmed bookings
                check_out__gte=timezone.now().date()  # Booking hasn't ended yet
            ).exists()
            
            if active_booking:
                return Response(
                    {"error": "You already have an active booking for this house"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
                
            # Initialize the serializer with the incoming data
            serializer = self.serializer_class(data=request.data)
            
            if serializer.is_valid():
                # Save the reservation instance with the provided data
                # Set booking=False initially since payment hasn't been made yet
                reservation = serializer.save(house=house, user=user, booking=False)
                
                # Calculate the total price after saving
                total_price = reservation.calculate_total_price()
                
                return Response(
                    {
                        "message": "Reservation created successfully. Please proceed to payment.",
                        "reservation_details": serializer.data,
                        "payment": total_price,
                        "reservation_id": reservation.id
                    },
                    status=status.HTTP_201_CREATED,
                )
            return Response({"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            
        except ReservationContents.DoesNotExist:
            return Response({"error": "House not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CustomerDetailsHousingView(APIView):
    """Handles customer reservation and payment initiation"""
    permission_classes = [IsAuthenticated]
    serializer_class = ReservationDetailSerializer
    
    def check_conflicting_bookings(self, house_id, check_in, check_out, current_reservation_id=None):
        """
        Check if there are any conflicting bookings for the house during the specified period.
        Excludes the current reservation if updating.
        """
        conflicting_reservations = ReservationDetails.objects.filter(
            house_id=house_id,
            booking=True,  # Only consider confirmed bookings
            check_out__gt=check_in,  # Checkout date is after the requested check-in
            check_in__lt=check_out   # Check-in date is before the requested checkout
        )
        
        # If we're updating an existing reservation, exclude it from the conflict check
        if current_reservation_id:
            conflicting_reservations = conflicting_reservations.exclude(id=current_reservation_id)
            
        # If any conflicting reservations exist, return False with a message
        if conflicting_reservations.exists():
            return False, "This house is already booked for the selected dates."
            
        return True, "No conflicting bookings found."
    
    
    
    def post(self, request, id):
        """Updates reservation and initiates payment"""
        user = request.user
        
        try:
            house = get_object_or_404(ReservationContents, id=id)
            
            # Find the user's pending reservation for this house
            try:
                # Get the latest reservation that hasn't been confirmed yet (booking=False)
                # or the reservation being explicitly updated by ID
                reservation_id = request.data.get('reservation_id')
                
                if reservation_id:
                    # If a specific reservation ID is provided, use that one
                    reservation = get_object_or_404(
                        ReservationDetails, 
                        id=reservation_id, 
                        house=house,
                        user=user
                    )
                else:
                    # Otherwise, get the latest unconfirmed reservation
                    reservation = ReservationDetails.objects.filter(
                        house=house, 
                        user=user,
                        booking=False
                    ).latest('created')  # Try using created_at field
            except (ReservationDetails.DoesNotExist):
                try:
                    # Try with 'created' field if 'created_at' doesn't exist
                    reservation = ReservationDetails.objects.filter(
                        house=house, 
                        user=user,
                        booking=False
                    ).latest('created')
                except ReservationDetails.DoesNotExist:
                    return Response(
                        {"error": "No pending reservation found. Please create a reservation first."},
                        status=status.HTTP_404_NOT_FOUND
                    )
            
            # Check for booking date conflicts if dates are being updated
            check_in = request.data.get('check_in') or reservation.check_in
            check_out = request.data.get('check_out') or reservation.check_out
            
            if check_in and check_out:
                # Convert string dates to date objects if needed
                if isinstance(check_in, str):
                    check_in = datetime.strptime(check_in, '%Y-%m-%d').date()
                if isinstance(check_out, str):
                    check_out = datetime.strptime(check_out, '%Y-%m-%d').date()
                    
                # Check for booking conflicts
                can_book, message = self.check_conflicting_bookings(
                    house.id, 
                    check_in, 
                    check_out,
                    reservation.id
                )
                
                if not can_book:
                    return Response({"error": message}, status=status.HTTP_400_BAD_REQUEST)
            
            # Initialize serializer with the reservation and request data
            serializer = self.serializer_class(
                reservation,
                data=request.data,
                context={'user': user},
                partial=True
            )
            
            if serializer.is_valid():
                updated_reservation = serializer.save()
                reference = str(uuid.uuid4())
                total_amount = updated_reservation.calculate_total_price()
                
                # Initiate payment
                email = user.email
                flutterwave_url = f"{settings.FLW_API_URL}/payments"
                secret_key = settings.FLW_SECRET_KEY
                vercel_url = getattr(settings, "VERCEL_APP_URL", None)
                
                payload = {
                    "tx_ref": reference,
                    "amount": float(total_amount),
                    "currency": "NGN",
                    "redirect_url": f"{vercel_url}/confirmation/",
                    "payment_type": "card",
                    "customer": {
                        "email": user.email,
                        "username": user.first_name
                    }
                }
                
                headers = {
                    "Authorization": f"Bearer {secret_key}",
                    "Content-Type": "application/json",
                }
                
                try:
                    response = requests.post(flutterwave_url, json=payload, headers=headers)
                    response_data = response.json()
                    
                    if response.status_code == 200 and response_data.get("status") == "success":
                        payment = Payment.objects.create(
                            user=user,
                            reservation=updated_reservation,
                            reference=reference,
                            total_amount=total_amount,
                            house=house
                        )
                        
                        # Fix: Correctly set payment status
                        payment.status = Payment.Status.PENDING
                        payment.save()
                        
                        # Only set booking=True after payment is initiated
                        updated_reservation.booking = True
                        updated_reservation.save()
                        
                        return Response({
                            "message": "Reservation updated and payment initiated successfully!",
                            "customer_id": updated_reservation.id,
                            "reservation_details": serializer.data,
                            "payment_link": response_data["data"]["link"],
                            "reference": reference,
                        }, status=status.HTTP_201_CREATED)
                    
                    return Response(
                        {"error": "Failed to initiate payment", "details": response_data}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
                    
                except requests.exceptions.RequestException as e:
                    return Response(
                        {"error": "Payment initiation failed", "details": str(e)}, 
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR
                    )
            
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
        except ReservationContents.DoesNotExist:
            return Response({"error": "House not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    

# class CreateGuests(APIView):
#     permission_classes = [IsAuthenticated]
#     serializer_class = GuestsSerializers
    
#     def post(self, request, post_pk):
#         user = request.user
        
#         try:
#             house = get_object_or_404(ReservationContents, id=post_pk)
            
#             # Check if the user already has an active booking for this house
#             active_booking = ReservationDetails.objects.filter(
#                 house=house,
#                 user=user,
#                 booking=True,
#                 check_out__gte=timezone.now().date()
#             ).exists()
            
#             if active_booking:
#                 return Response(
#                     {"error": "You already have an active booking for this house"}, 
#                     status=status.HTTP_400_BAD_REQUEST
#                 )
                
#             # Initialize the serializer with the incoming data
#             serializer = self.serializer_class(data=request.data)
            
#             if serializer.is_valid():
#                 # Save the reservation instance with the provided data
#                 reservation = serializer.save(house=house, user=user)
#                 reservation.booking = True
#                 reservation.save()
                
#                 # Calculate the total price after saving
#                 total_price = reservation.calculate_total_price()
                
#                 return Response(
#                     {
#                         "message": "Reservation and Payment initiated successfully.",
#                         "reservation_details": serializer.data,
#                         "payment": total_price
#                     },
#                     status=status.HTTP_201_CREATED,
#                 )
#             return Response({"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            
#         except ReservationContents.DoesNotExist:
#             return Response({"error": "House not found"}, status=status.HTTP_404_NOT_FOUND)
#         except Exception as e:
#             return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    
    
    

# class CustomerDetailsHousingView(APIView):
#     """Handles customer reservation and payment initiation"""
#     permission_classes = [IsAuthenticated]
#     serializer_class = ReservationDetailSerializer
    
#     def check_conflicting_bookings(self, house_id, check_in, check_out, current_reservation_id=None):
#         """
#         Check if there are any conflicting bookings for the house during the specified period.
#         Excludes the current reservation if updating.
#         """
#         conflicting_reservations = ReservationDetails.objects.filter(
#             house_id=house_id,
#             booking=True,  # Only consider confirmed bookings
#             check_out__gt=check_in,  # Checkout date is after the requested check-in
#             check_in__lt=check_out   # Check-in date is before the requested checkout
#         )
        
#         # If we're updating an existing reservation, exclude it from the conflict check
#         if current_reservation_id:
#             conflicting_reservations = conflicting_reservations.exclude(id=current_reservation_id)
            
#         # If any conflicting reservations exist, return False with a message
#         if conflicting_reservations.exists():
#             return False, "This house is already booked for the selected dates."
            
#         return True, "No conflicting bookings found."
    
    
    
    
#     def post(self, request, id):
#         """Updates reservation and initiates payment"""
#         #post = get_object_or_404(ReservationContents, id=post_id)  # Ensure post exists
#         user = request.user
#         house = ReservationContents.objects.get(id=id)
#         reservation = ReservationDetails.objects.filter(house=house, user=user).latest('created')
#         date_fix = reservation.check_out
        
#         can_book, message = self.can_make_new_booking(id, user.id)
#         if not can_book:
#             return Response({"error": message}, status=400)
        
#         if reservation:
#             print(f"reservation_value: {reservation}")
#             print(f"check_out_now: {date_fix}")
#         serializer = ReservationDetailSerializer(
#             reservation,
#             data=request.data,
#             context={'user': user},
#             partial=True
#         )
#         print(serializer)

#         if serializer.is_valid():
#             updated_reservation = serializer.save()
#             reference = str(uuid.uuid4())
#             total_amount = updated_reservation.calculate_total_price()
#             print(total_amount)

#             # Initiate payment
#             email = user.email
#             reference = str(uuid.uuid4())
#             flutterwave_url = f"{settings.FLW_API_URL}/payments"
#             paystack_url_initialize = f"{settings.PAYSTACK_URL_INITIALIZE}"
#             paystack_url_verify = f"{settings.PAYSTACK_URL_VERIFY}"
#             paystack_secret_key = f"{settings.PAYSTACK_SECRET_KEY}"
            
#             secret_key = settings.FLW_SECRET_KEY
#             vercel_url = getattr(settings, "VERCEL_APP_URL", None)

#             payload = {
#                 "tx_ref": reference,
#                 "amount": float(total_amount),
#                 "currency": "NGN",
#                 "redirect_url": f"{vercel_url}/confirmation/",
#                 "payment_type": "card",
#                 "customer": {"email": user.email,
#                              "username":user.first_name}
#             }
            
#             headers = {
#                 "Authorization": f"Bearer {secret_key}",
#                 "Content-Type": "application/json",
#             }
            
            
            
            
#             data = {
#                 "tx_ref": reference,
#                 "email": email,
#                 "amount": float(total_amount * 100),
#                 "reference": reference,
#                 "callback_url": f"{vercel_url}/confirmation/",
#             }

#             headers_paystack = {
#                     "Authorization": f"Bearer {paystack_secret_key}",
#                     "Content-Type": "application/json",
#             }

#             try:
#                 response = requests.post(flutterwave_url, json=payload, headers=headers)
#                 response_data = response.json()
                
               
#                 if response.status_code == 200 and response_data.get("status") == "success":
#                     payment=Payment.objects.create(
#                         user=user,
#                         reservation=reservation,
#                         reference=reference,
#                         total_amount=total_amount,
#                         house = house
#                     )
                   
#                     payment.Status.PENDING
#                     updated_reservation.booking = True
#                     updated_reservation.save()
#                     return Response({
#                         "message": "Reservation updated and payment initiated successfully!",
#                         "customer_id": updated_reservation.id,
#                         "reservation_details": serializer.data,
#                         "payment_link": response_data["data"]["link"],
#                         "reference": reference,
#                     }, status=201)
                    
#                 # response_paystack = requests.post(paystack_url_initialize, json=data, headers=headers_paystack)
#                 # response_data_paystack = response_paystack.json()
#                 # check1= response_data_paystack["data"]["reference"]
#                 # print(f"reference: {reference}")
#                 # print(f"check1: {check1}")
#                 # if response_paystack.status_code ==200 and response_data_paystack.get("status") == "success":
#                 #         payment=Payment.objects.create(
#                 #             user=user,
#                 #             reservation=reservation,
#                 #             reference=response_data_paystack["data"]["reference"],
#                 #             total_amount=total_amount,
#                 #             house = house
#                 #         )
#                 #         payment.Status.PENDING
#                 #         return Response({
#                 #             "message": "Reservation updated and payment initiated successfully!",
#                 #             "customer_id": updated_reservation.id,
#                 #             "reservation_details": serializer.data,
#                 #             "payment_link": response_data_paystack["data"]["authorization_url"],
#                 #             "reference": reference,
#                 #         }, status=201)

#                 return Response({"error": "Failed to initiate payment"}, status=400)    

#             except requests.exceptions.RequestException:
#                 return Response({"error": "Payment initiation failed"}, status=500)

#         return Response(serializer.errors, status=400)
