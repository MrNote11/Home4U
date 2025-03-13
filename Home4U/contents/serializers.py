from rest_framework import serializers
from .models import (ReservationContents, ReservationImages,
                     PostRating, ReservationDetails,
                     PostLike)
from django.utils import timezone
import re
from django.db.models import Sum, Count
from django.contrib.auth import get_user_model

class ReservationImagesSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReservationImages
        fields = ['image_url']

class ReservationDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReservationDetails
        fields = ('first_name', 'last_name', 'phone_number', 'email')
        
    def validate_phone_number(self, value):
        """Validate phone number format"""
        phone_pattern = r'^\+?1?\d{9,15}$'  # Validates phone numbers like +123456789 or 123456789
        if not re.match(phone_pattern, value):
            raise serializers.ValidationError("Invalid phone number format.")
        return value

    def create(self, validated_data):
        user = self.context.get('user')  # Get the current authenticated user
        post = self.context.get('post')  # Get the post from the context
        
        if not post:
            raise serializers.ValidationError("Post not provided.")
        
        # Create the ReservationDetails instance (reservation details)
        post_rating = ReservationDetails.objects.create(
            user=user,
            post=post,
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            phone_number=validated_data['phone_number'],
            email=validated_data['email']
        )
        return post_rating  # Return the created ReservationDetails instance



class ReservationContentsSerializer(serializers.ModelSerializer):
    likes_count = serializers.SerializerMethodField()
    images = ReservationImagesSerializer(many=True)  # Serialize many images
    # ratings_counts = serializers.SerializerMethodField()
    ratings_reviews = serializers.SerializerMethodField()
    average_rating = serializers.FloatField(read_only=True)
    
    class Meta:
        model = ReservationContents
        
        fields = ['id', 'house', 'beds', 'price', 'address', 'state', 'swimmingpool',
                  'wifi','ratings_reviews', 'country', 
                  'images', 'average_rating',
                  'likes_count', 'description', 'status']  

    def get_likes_count(self, obj):
        return PostRating.objects.filter(post=obj).count()
    
    def get_ratings_reviews(self, obj):
        # Count the number of distinct users who have rated the current post
        return PostRating.objects.filter(post=obj).values('user').distinct().count()
    
    def get_ratings_counts(self, obj):
        user = self.context.get('user')
        user_ratings = PostRating.objects.filter(user=user, post=obj)

        if user_ratings.exists():
            # Sum of ratings for the current user for this post
            ratings_sum = user_ratings.aggregate(Sum('ratings'))['ratings__sum']
            # Return the sum of ratings instead of dividing by 2
            return ratings_sum
        return 0


class PostRatingSerializer(serializers.ModelSerializer):
    post = ReservationContentsSerializer()
    rating_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = ReservationContents
        fields = ['id', 'house', 'state', 'country', 'average_rating', 'rating_count']


class PostLikeSerializer(serializers.ModelSerializer):
    # user = serializers.StringRelatedField()  # Display username
    post = ReservationContentsSerializer()

    class Meta:
        model = PostLike
        fields = ['id', 'post', 'created_at']

   

class GuestsSerializers(serializers.ModelSerializer):
    class Meta:
        model = ReservationDetails
        fields = ['check_in', 'check_out', 'guests']

    def validate_check_in(self, value):
        if value < timezone.now().date():
            raise serializers.ValidationError("Check-in date cannot be in the past.")
        return value

    def validate_check_out(self, value):
        if value < timezone.now().date():
            raise serializers.ValidationError("Check-out date cannot be in the past.")
        return value
    

    def validate(self, attrs):
        check_in = attrs.get('check_in')
        check_out = attrs.get('check_out')

        if check_in and check_out:
            if check_out <= check_in:
                raise serializers.ValidationError("Check-out must be after check-in.")
        
        if check_in == check_out:
            raise serializers.ValidationError("Check-in and check-out cannot be the same.")
        
        return attrs
    
    def create(self, validated_data):
        user = self.context.get('user')
        post_id = self.context.get('post')  # This is the post ID passed in the context

        # Fetch the ReservationContents instance using the post_id
        post = ReservationContents.objects.get(id=post_id)  # Make sure the post exists

        check_in = validated_data.get('check_in')
        check_out = validated_data.get('check_out')
        guests = validated_data.get('guests')

        # Create the PostRating instance with the correct post object
        post_rating = ReservationDetails.objects.create(
            user=user,
            post=post,  # Pass the actual ReservationContents instance, not just the ID
            check_in=check_in,
            check_out=check_out,
            guests=guests
        )
        return post_rating

class UserPostRatingSerializer(serializers.ModelSerializer):
    # Serialize the related ReservationContents data (Post)
    post = ReservationContentsSerializer()
    
    class Meta:
        model = PostRating
        fields = ['post', 'ratings', 'check_in', 'check_out', 'first_name', 'last_name', 'phone_number', 'guests']

    def to_representation(self, instance):
        user = self.context.get('user')  # Get the authenticated user from context
        post = self.context.get('post')  # Get the related ReservationContents instance
        
        # Return a representation that includes both the rating and the related post data
        return {
            'user': user,
            'house': post.house,
            'address': post.address,

        }
