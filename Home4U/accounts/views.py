from rest_framework.response import Response
from rest_framework import status, views
from rest_framework.views import APIView
from rest_framework import generics
from rest_framework.exceptions import ValidationError
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.models import User

from .serializers import (UserSerializers,
                          UpdateSerializers, ResendOTPSerializer,
                          ForgotPasswordSerializer, ResetPasswordSerializer,
                          LoginSerializer, LogoutSerializer)

from .models import VerificationToken, UserProfile
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied, NotFound
from django.core.mail import send_mail
from django.conf import settings
from django.urls import reverse
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import send_mail
from django.utils import timezone
from django.shortcuts import redirect


class UserRegister(APIView):
    def post(self, request):
        serializer = UserSerializers(data=request.data, context={'request': request})

        if serializer.is_valid(raise_exception=True):
            email = serializer.validated_data['email']
            username = serializer.validated_data['username']
            resend = request.query_params.get('resend') == 'true'
            purpose= VerificationToken.Choices.REGISTERATION
            try:
                user = User.objects.get(email=email)
                if user.is_active:
                    return Response({"message": "User already registered and active."}, status=status.HTTP_400_BAD_REQUEST)
                elif resend:
                    # Resend OTP
                    VerificationToken.objects.filter(user=user, is_used=False, expires_at__lt=timezone.now()).delete()
                    token, created = VerificationToken.objects.get_or_create(user=user, purpose=purpose)
                    uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
                    verification_link = request.build_absolute_uri(reverse('verify-otp', kwargs={'uidb64': uidb64, 'token': token}))
                    send_mail(
                        'Verify Your Account (New OTP)',
                        f'Click the following link within 10 minutes to verify your account: {verification_link}',
                        settings.EMAIL_HOST_USER,
                        [user.email],
                        fail_silently=False
                    )
                    return Response({"message": "New verification link sent."}, status=status.HTTP_200_OK)
                else:
                    return Response({"message": "User already registered, but not activated. Please use resend=true query parameter"}, status=status.HTTP_400_BAD_REQUEST)

            except User.DoesNotExist:
                user = serializer.save()
                user.is_active = False
                user.save()
                token, created = VerificationToken.objects.get_or_create(user=user, purpose=purpose)
                uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
                verification_link = request.build_absolute_uri(reverse('verify-otp', kwargs={'uidb64': uidb64, 'token': token}))
                send_mail(
                    'Verify Your Account',
                    f'Click the following link within 10 minutes to verify your account: {verification_link}',
                    settings.EMAIL_HOST_USER,
                    [user.email],
                    fail_silently=False
                )
                return Response({"message": "Verification link sent. Click within 10 minutes.", "data": serializer.data}, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

signup = UserRegister.as_view()

  

class VerifyOTPView(APIView):
    def get(self, request, uidb64, token):
        try:
            user_id = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=user_id)
            verification_token = VerificationToken.objects.get(user=user, token=token, is_used=False)

            if verification_token.is_expired():
                user.delete()
                return Response({"message": "OTP has expired."}, status=status.HTTP_400_BAD_REQUEST)

            user.is_active = True
            user.save()
            verification_token.is_used = True
            verification_token.delete()
            
            
            # Redirect with query parameters
            vercel_url = settings.VERCEL_APP_URL  # Get the base URL from settings
            redirect_url = f"{vercel_url}/?verified=true&email={user.email}"

            return redirect(redirect_url)

        except (User.DoesNotExist, VerificationToken.DoesNotExist):
            return Response({"message": "Invalid or expired OTP."}, status=status.HTTP_400_BAD_REQUEST)


class LoginView(views.APIView):
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            refresh = RefreshToken.for_user(user)
            access_token = refresh.access_token

            # Check if the user has a profile and save it
            try:
                user_profile = user.userprofile
                profile_image = request.build_absolute_uri(user_profile.profile_image.url) if user_profile.profile_image else None
            except UserProfile.DoesNotExist:
                profile_image = None

            # if user_profile:
            #     user_profile.save()

            return Response({
                'refresh': str(refresh),
                'access': str(access_token),
                'data': {
                    'username': user.username,
                    'profile_image': request.build_absolute_uri(profile_image) if profile_image else None,
                }
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



class UpdateView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        try:
            profile = UserProfile.objects.get(user=request.user)
        except UserProfile.DoesNotExist:
            raise NotFound("User profile does not exist.")

        serializer = UpdateSerializers(profile, data=request.data, partial=True, context={'request': request})

        if serializer.is_valid():
            serializer.save()
            return Response({
                "message": "Profile updated successfully",
                "data": serializer.data
            }, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


update = UpdateView.as_view()   


class ForgotPasswordView(generics.CreateAPIView):
    serializer_class = ForgotPasswordSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({"error": "User with this email does not exist."}, status=status.HTTP_404_NOT_FOUND)

        # Delete any existing password reset OTPs for the user
        OTP.objects.filter(user=user, purpose='password_reset', is_used=False, expires_at__gt=timezone.now()).delete()

        otp_instance = OTP.objects.create(user=user, purpose='password_reset')
        try:
            send_mail(
                'Reset Your Password',
                f'Your OTP for password reset is: {otp_instance.otp}',
                settings.EMAIL_HOST_USER,
                [email],
                fail_silently=False,
            )
            return Response({"message": "Password reset OTP sent to your email."}, status=status.HTTP_200_OK)
        except Exception as err:
            print(err)
            
            
class ResetPasswordView(generics.CreateAPIView):
    serializer_class = ResetPasswordSerializer
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        otp = serializer.validated_data['otp']
        new_password = serializer.validated_data['new_password']

        try:
            otp_instance = OTP.objects.get(otp=otp, purpose='password_reset', is_used=False)

            if otp_instance.is_expired():
                return Response({"error": "OTP has expired."}, status=status.HTTP_400_BAD_REQUEST)

            user = otp_instance.user
            user.set_password(new_password)
            user.save()

            otp_instance.is_used = True
            otp_instance.save()

            return Response({"message": "Password reset successfully."}, status=status.HTTP_200_OK)

        except OTP.DoesNotExist:
            return Response({"error": "Invalid OTP."}, status=status.HTTP_400_BAD_REQUEST)


class LogoutView(APIView):
    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        if serializer.is_valid():
            refresh_token = serializer.validated_data['refresh_token']
            try:
                token = RefreshToken(refresh_token)
                token.blacklist()  # Blacklisting the refresh token
                return Response({"message": "Logged out successfully."}, status=status.HTTP_200_OK)
            except Exception as e:
                return Response({"message": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
