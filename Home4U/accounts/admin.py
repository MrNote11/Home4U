from django.contrib import admin

from .models import UserProfile, VerificationToken
from django.contrib.auth.models import User

# admin.site.register(get_user_model)  
admin.site.register(UserProfile)
admin.site.register(VerificationToken)
# admin.site.register(User)  
