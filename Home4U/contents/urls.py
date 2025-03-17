from django.urls import path, include
from .views import  (HomeView, CreateGuests,   #deletelikepost,
                    # likedpost, likedview,
                    #  new_post, rating, top_post, top_rating,
                     )
from django.conf import settings
from django.conf.urls.static import static
from rest_framework import routers
from rest_framework_nested.routers import NestedDefaultRouter
from .views import (CreateGuests, ReservationRatingView, #likedpost,
                    LikePostView, UserLikedPostsView,
                    FilteredPostRatingsView,
                    UnlikePostView, HomeView,
                    HomeViewdetails, TopHomeView,
                                     CustomerDetailsViews,
                    FilteredPostRatingsView)#, likedview)


urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('<int:pk>/', HomeViewdetails.as_view(), name='description'),
    path('<int:post_pk>/create/', CreateGuests.as_view(), name='create'),
    path('<int:pk>/like/', LikePostView.as_view(), name='house_like'),
    path('likedview/', UserLikedPostsView.as_view(), name='likedview'),
    path('<int:pk>/delete/', UnlikePostView.as_view(), name='deletelike'),
    path('newly/', TopHomeView.as_view(), name='new_posts'),
    path('<int:post_pk>/ratings/', ReservationRatingView.as_view(), name='rating_posts'),
    path('<int:post_id>/customer_input/', CustomerDetailsViews.as_view(), name='customer-input'),
    path('top_post/', FilteredPostRatingsView.as_view(), name='top-post'),
    path('ratings/', FilteredPostRatingsView.as_view(), name='filtered-post-ratings'),

]
