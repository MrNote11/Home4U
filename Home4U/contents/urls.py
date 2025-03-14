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
router = routers.DefaultRouter()
router.register('reservation', HomeView)

urlpatterns = [
    path('reservation/', HomeView.as_view(), name='home'),
    path('reservation/<int:pk>/', HomeViewdetails.as_view(), name='description'),
    path('reservation/<int:post_pk>/create/', CreateGuests.as_view(), name='create'),
    path('reservation/<int:pk>/like/', LikePostView.as_view(), name='house_like'),
    path('reservation/likedview/', UserLikedPostsView.as_view(), name='likedview'),
    path('reservation/<int:pk>/delete/', UnlikePostView.as_view(), name='deletelike'),
    path('reservation/newly/', TopHomeView.as_view(), name='new_posts'),
    path('reservation/<int:post_pk>/ratings/', ReservationRatingView.as_view(), name='rating_posts'),
    path('reservation/<int:post_id>/customer_input/', CustomerDetailsViews.as_view(), name='customer-input'),
    path('reservation/top_post/', FilteredPostRatingsView.as_view(), name='top-post'),
    path('reservation/ratings/', FilteredPostRatingsView.as_view(), name='filtered-post-ratings'),

]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    #https://documenter.getpostman.com/view/39412368/2sAYXBFyoT