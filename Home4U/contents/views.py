
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
        bookings = ReservationDetails.objects.filter(user=user)

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
        house = get_object_or_404(ReservationContents, id=post_pk)
        
        # Initialize the serializer with the incoming data
        serializer = self.serializer_class(data=request.data)
        
        if serializer.is_valid():
            # Save the reservation instance with the provided data
            reservation = serializer.save(house=house, user=user)
            reservation.booking = True
            reservation.save()
            
            # Calculate the total price after saving
            total_price = reservation.calculate_total_price()
            
            return Response(
                {
                    "message": "Reservation and Payment initiated successfully.",
                    "reservation_details": serializer.data,
                    "payment": total_price
                },
                status=status.HTTP_201_CREATED,
            )
        return Response({"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
    
    



class CustomerDetailsHousingView(APIView):
    """Handles customer reservation and payment initiation"""
    permission_classes = [IsAuthenticated]
    serializer_class = ReservationDetailSerializer

    def post(self, request, id):
        """Updates reservation and initiates payment"""
        #post = get_object_or_404(ReservationContents, id=post_id)  # Ensure post exists
        user = request.user
        house = ReservationContents.objects.get(id=id)
        reservation = ReservationDetails.objects.filter(house=house, user=user).last()
        
        print(f"reservation_value: {reservation}")
        
        serializer = ReservationDetailSerializer(
            reservation,
            data=request.data,
            context={'user': user},
            partial=True
        )
        print(serializer)

        if serializer.is_valid():
            updated_reservation = serializer.save()
            reference = str(uuid.uuid4())
            total_amount = updated_reservation.calculate_total_price()
            print(total_amount)

            # Initiate payment
            email = user.email
            reference = str(uuid.uuid4())
            flutterwave_url = f"{settings.FLW_API_URL}/payments"
            secret_key = settings.FLW_SECRET_KEY
            vercel_url = getattr(settings, "VERCEL_APP_URL", None)

            payload = {
                "tx_ref": reference,
                "amount": float(total_amount),
                "currency": "NGN",
                "redirect_url": f"{vercel_url}/confirmation/",
                "payment_type": "card",
                "customer": {"email": user.email,
                             "username":user.first_name}
            }

            headers = {
                "Authorization": f"Bearer {secret_key}",
                "Content-Type": "application/json",
            }

            try:
                response = requests.post(flutterwave_url, json=payload, headers=headers)
                response_data = response.json()

                if response.status_code == 200 and response_data.get("status") == "success":
                    payment=Payment.objects.create(
                        user=user,
                        reservation=reservation,
                        reference=reference,
                        total_amount=total_amount,
                        house = house
                    )
                    payment.Status.PENDING
                    return Response({
                        "message": "Reservation updated and payment initiated successfully!",
                        "customer_id": updated_reservation.id,
                        "reservation_details": serializer.data,
                        "payment_link": response_data["data"]["link"],
                        "reference": reference,
                    }, status=201)

                return Response({"error": "Failed to initiate payment"}, status=400)

            except requests.exceptions.RequestException:
                return Response({"error": "Payment initiation failed"}, status=500)

        return Response(serializer.errors, status=400)
