
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
            average_rating=Round(Avg('ratings__ratings')),  # ✅ Force rounding at DB level
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
    lookup_field = 'pk'
    
    def get_queryset(self):
        # Assuming you are passing `post_id` in the URL and want to filter by post_id
        post_id = self.kwargs['post_pk']
        return PostRating.objects.filter(post_id=post_id)

    def get_serializer_context(self):
        # Retrieve the current user and post from the request and URL
        user = self.request.user
        post_id = self.kwargs['post_pk']  # Retrieve the post_id from the URL
        
        # Return the context with both user and post
        return {
            'user': user,
            'post': post_id  # Post will be used in the serializer to create a PostRating instance
        }



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
        try:
            # Fetch the post (reservation) by ID
            post = ReservationContents.objects.get(pk=post_id)
        except ReservationContents.DoesNotExist:
            raise NotFound(detail="Reservation not found.")

        # Add the post and user to the serializer context
        serializer = ReservationDetailSerializer(
            data=request.data,
            context={'post': post, 'user': self.request.user}  # Ensure correct user is passed
        )

        if serializer.is_valid():
            post_rating = serializer.save()  # Save the ReservationDetails instance
            
            # Return a response with the serializer data and a success message
            return Response({
                'message': 'Reservation created successfully!',
                'customer_id': post_rating.id,
                'reservation_details': serializer.data
            }, status=201)  # HTTP 201 Created response

        return Response(serializer.errors, status=400)  # If the data is invalid, return the errors



