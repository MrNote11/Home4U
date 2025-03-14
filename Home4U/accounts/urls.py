from django.conf import settings
from django.urls import path
from django.conf.urls.static import static
from .views import (
    signup,
    LoginView,
    ForgotPasswordView,
    ResetPasswordView,
    LogoutView,
    update,
    VerifyOTPView,
    resend_otp
    
    # profile
    # customdetails
)
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView
)



urlpatterns = [
    path('signup/', signup, name='signup'),
    path('login/', LoginView.as_view(), name='login'),
    path('forgot-password/', ForgotPasswordView.as_view(), name='forgot-password'),  # Forgot Password
    path('reset-password/', ResetPasswordView.as_view(), name='reset-password'),  # Reset Password
    path('logout/', LogoutView.as_view(), name='logout'),  # User logout
    path('update-profile/', update, name='update'),
    path('verify-otp/<str:uidb64>/<str:token>/', VerifyOTPView.as_view(), name='verify-otp'),
    path('resend-otp/', resend_otp, name='resend-otp'),

    
    # path('profile/', profile, name='profile')
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    

    