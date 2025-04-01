
from .models import ReservationContents, PostRating, ReservationDetails, PostLike
from rest_framework import status, generics
from rest_framework.response import Response
from rest_framework import filters
from rest_framework.views import APIView
from .serializers import (ReservationContentsSerializer, GuestsSerializers, 
                          ReservationDetailSerializer,
                          PostLikeSerializer
                          )
from .paginations import Limits
from django_filters.rest_framework import DjangoFilterBackend
from .filters import ReservationFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import NotFound
from django.db.models import Avg, Count, Value, FloatField, Func
from django.shortcuts import get_object_or_404
import uuid
from payments.models import Payment
from django.conf import settings
import requests


class Round(Func):
    function = 'ROUND'
    template = "%(function)s(%(expressions)s, 1)"

class HomeViews(generics.ListAPIView):
    serializer_class = ReservationContentsSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = Limits
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = ReservationFilter
    search_fields = ['house', 'state']

    def get_queryset(self):
        queryset = ReservationContents.objects.annotate(
            average_rating=Round(Avg('ratings__ratings')),  
            total_raters=Count('ratings__user', distinct=True),
            total_likes=Count('post_likes')
        )

        global_avg = PostRating.objects.aggregate(global_avg=Avg('ratings'))['global_avg']
        self.global_avg_rating = round(global_avg, 1) if global_avg else 0  # ✅ Round Python-level

        query_params = self.request.query_params
        homepage_filter = query_params.get('homepage')

        if homepage_filter == 'home':
            reservation_id = query_params.get('id')
            if reservation_id and reservation_id.isdigit():
                return queryset.filter(id=int(reservation_id))
            return queryset.order_by("created")

        elif homepage_filter == 'newly added':
            return queryset.order_by("-created")

        elif homepage_filter == 'ratings':
            post_ids = PostRating.objects.filter(ratings__gte=3).values_list('post_id', flat=True)
            return queryset.filter(id__in=post_ids)

        return queryset.none()


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



class ReservationRatingView(APIView):
    def post(self, request, post_pk, *args, **kwargs):
        rating = request.data.get("ratings")
        user = request.user

        if not user:
            return Response({"error": "User cannot be None"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            apartment = ReservationContents.objects.get(pk=post_pk)

            # Ensure user has booked the apartment
            # if not ReservationDetails.objects.filter(user=user, post=apartment).exists():
            #     return Response({"error": "You haven't booked this house"}, status=status.HTTP_400_BAD_REQUEST)

            # Create rating if user has booked the apartment
            apartment_rating = PostRating.objects.create(post=apartment, user=user, ratings=rating)
            serialized_apartment = ReservationContentsSerializer(apartment).data
            return Response({
                "detail": serialized_apartment,
                "message": "Successfully rated"
            }, status=status.HTTP_200_OK)

        except ReservationContents.DoesNotExist:
            return Response({"error": "ReservationContents with such ID does not exist"}, status=status.HTTP_404_NOT_FOUND)

        except Exception as err:
            import traceback
            return Response({"error": str(err), "detailed_error": traceback.format_exc()}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        


class CreateGuests(generics.CreateAPIView):
    queryset = ReservationDetails.objects.all()
    serializer_class = GuestsSerializers
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        post_id = self.kwargs.get('post_pk')
        return ReservationDetails.objects.filter(post_id=post_id)

    def get_serializer_context(self):
        user = self.request.user
        post_id = self.kwargs.get('post_pk')
        return {'user': user, 'post': int(post_id) if post_id else None}

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            reservation = serializer.save()
            user = self.request.user
            total_amount = reservation.calculate_total_price()

            if total_amount <= 0:
                return Response({"error": "Invalid total price"}, status=status.HTTP_400_BAD_REQUEST)

            # Store check_in, check_out, and total_amount in session
            request.session['check_in'] = str(reservation.check_in)
            request.session['check_out'] = str(reservation.check_out)
            request.session['total_amount'] = float(total_amount)

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
                            "message": "Reservation and Payment initiated successfully.",
                            "reservation_details": serializer.data,
                            "payment_link": response_data["data"]["link"],
                            "reference": reference,
                        },
                        status=status.HTTP_201_CREATED,
                    )

                return Response({"error": "Failed to initiate payment"}, status=status.HTTP_400_BAD_REQUEST)

            except requests.exceptions.RequestException:
                return Response({"error": "Payment initiation failed"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            except Exception as e:
                return Response({"error": f"Database or unexpected error: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
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


class CustomerDetailsViews(generics.CreateAPIView):
    serializer_class = ReservationDetailSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request, post_id):
        post = get_object_or_404(ReservationContents, pk=post_id)
        user = request.user

        # Retrieve values from session
        check_in = request.session.get('check_in')
        check_out = request.session.get('check_out')
        total_amount = request.session.get('total_amount')

        if not check_in or not check_out or total_amount is None:
            return Response({'error': 'Missing data in session'}, status=400)

        # Add check_in and check_out to request data
        mutable_data = request.data
        mutable_data['check_in'] = check_in
        mutable_data['check_out'] = check_out

        serializer = ReservationDetailSerializer(
            data=mutable_data,
            context={'post': post, 'user': user}
        )

        if serializer.is_valid():
            reservation = serializer.save()

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
                            "message": "Reservation created and payment initiated successfully!",
                            "customer_id": reservation.id,
                            "reservation_details": serializer.data,
                            "customer_details": reservation.customer_details,
                            "total":total_amount,
                            "payment_link": response_data["data"]["link"],
                            "reference": reference,
                        },
                        status=201,
                    )

                return Response({"error": "Failed to initiate payment"}, status=status.HTTP_400_BAD_REQUEST)

            except requests.exceptions.RequestException:
                return Response({"error": "Payment initiation failed"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            except Exception as e:
                return Response({"error": f"Database or unexpected error: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(serializer.errors, status=400)