from django.contrib import admin
from .models import ReservationContents, ReservationImages, PostRating, PostLike, ReservationDetails


admin.site.register(ReservationDetails)
admin.site.register(PostRating)
admin.site.register(ReservationContents)
admin.site.register(ReservationImages)
admin.site.register(PostLike)
# Register your models here.
