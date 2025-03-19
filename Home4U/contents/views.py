
from .models import ReservationContents, PostRating, ReservationDetails
from rest_framework import status, generics
from rest_framework.response import Response
from rest_framework import viewsets
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from .serializers import (ReservationContentsSerializer, GuestsSerializers, 
                          ReservationDetailSerializer,
                          PostLikeSerializer
                          )
from .paginations import Limits
from rest_framework import filters
from django_filters.rest_framework import DjangoFilterBackend
from .filters import ReservationFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import NotFound
from .models import PostRating, ReservationContents, PostLike
from rest_framework.permissions import IsAuthenticated
from django.db.models import Avg, Count


class HomeViews(generics.ListAPIView):
    serializer_class = ReservationContentsSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = Limits
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = ReservationFilter
    search_fields = ['house', 'state']

    def get_queryset(self):
        queryset = ReservationContents.objects.all().annotate(
            average_rating=Avg('ratings__ratings')*1
        )
        query_params = self.request.query_params

        if query_params.get('homepage') == 'home':
            reservation_id = query_params.get('id')
            if reservation_id and reservation_id.isdigit():
                return queryset.filter(id=int(reservation_id))
            return queryset.order_by("created")

        elif query_params.get('homepage') == 'newly added':
            return queryset.order_by("-created")

        elif query_params.get('homepage') == 'ratings':
            post_ids = PostRating.objects.filter(ratings__gte=3).values_list('post_id', flat=True)
            return queryset.filter(id__in=post_ids)

        return ReservationContents.objects.none()  # ✅ Corrected this line
  # Fixed syntax


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


# Customer Reservation Details View





class LikePostView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            reservation = ReservationContents.objects.get(pk=pk)
        except ReservationContents.DoesNotExist:
            return Response({'error': 'Reservation not found'}, status=status.HTTP_404_NOT_FOUND)

        user = request.user
        if PostLike.objects.filter(post=reservation, user=user).exists():
            return Response({'message': 'Reservation already liked'}, status=status.HTTP_200_OK)

        PostLike.objects.create(post=reservation, user=user)
        return Response({'message': 'Reservation liked'}, status=status.HTTP_201_CREATED)

class UnlikePostView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        try:
            reservation = ReservationContents.objects.get(pk=pk)
        except ReservationContents.DoesNotExist:
            return Response({'error': 'Reservation not found'}, status=status.HTTP_404_NOT_FOUND)

        user = request.user
        try:
            like = PostLike.objects.get(post=reservation, user=user)
            like.delete()
            return Response({'message': 'Reservation unliked'}, status=status.HTTP_200_OK)
        except PostLike.DoesNotExist:
            return Response({'message': 'Reservation not liked yet'}, status=status.HTTP_400_BAD_REQUEST)

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


        
        
class ReservationRatingView(APIView):
    
    def post(self, request, post_pk, *args, **kwargs):
        rating = request.data["ratings"]
        user = request.user
 
        if request.user is None:
            return Response({"error": "User can not be None"}, status=status.HTTP_400_BAD_REQUEST)
        
        
        # WRITE TO MAKE SURE ONLY IF YOU HAVE USED A BOOKED APARTMENT YOU WILL BE BALLE TO MAKE RATINGS

        try:
            apartment = ReservationContents.objects.get(pk=post_pk)
            # if ReservationDetails.objects.filter(user=request.user, post=apartment).exists():
            apartment_rating = PostRating.objects.create(
                    post=apartment,
                    user=request.user,
                    ratings=rating
                )
            apartment_rating.save()
            serialized_apartment = ReservationContentsSerializer(apartment).data
            return Response({
                    "detail": serialized_apartment,
                    "message": "Successfully"
                }, status=status.HTTP_200_OK)
            # else:
            #     return Response({"message": "You havent booked this house"})
        except ReservationContents.DoesNotExist:
            return Response({"error": "ReservationContents with such id does not exist"}, status=status.HTTP_404_NOT_FOUND)

        except Exception as err:
            import traceback
            return Response({"error": str(err),
                             "detailed_error": traceback.format_exc()}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)




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



