from django.contrib import admin

from .models import UserProfile, OTP
from django.contrib.auth.models import User

# admin.site.register(get_user_model)  
admin.site.register(UserProfile)
admin.site.register(OTP)
# admin.site.register(User)  
