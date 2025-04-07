from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from .views import (CreateGuests, ReservationRatingView, #likedpost,
                    LikePostView, UserLikedPostsView,
                    UnlikePostView, HomeViews, HomeDescriptions, 
                                     CustomerDetailsHousingView)


urlpatterns = [
    path('', HomeViews.as_view(), name='home'),
    path('<int:pk>/', HomeDescriptions.as_view(), name='description'),
    path('<int:post_pk>/create/', CreateGuests.as_view(), name='create'),
    path('<int:pk>/like/', LikePostView.as_view(), name='house_like'),
    path('likedview/', UserLikedPostsView.as_view(), name='likedview'),
    path('<int:pk>/delete/', UnlikePostView.as_view(), name='deletelike'),
    # path('newly/', TopHomeView.as_view(), name='new_posts'),
    path('<int:post_pk>/ratings/', ReservationRatingView.as_view(), name='rating_posts'),
    path('<int:id>/customer_input/', CustomerDetailsHousingView.as_view(), name='customer-input'),
    # path('top_post/', FilteredPostRatingsView.as_view(), name='top-post'),
    # path('ratings/', FilteredPostRatingsView.as_view(), name='filtered-post-ratings'),
]
