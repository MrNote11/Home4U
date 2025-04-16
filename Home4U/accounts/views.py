from rest_framework.response import Response
from rest_framework import status, views
from rest_framework.views import APIView
from rest_framework import generics
from rest_framework.exceptions import ValidationError
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.models import User

from .serializers import (UserSerializers,
                          UpdateSerializers,
                          ForgotPasswordSerializer, ResetPasswordSerializer,
                          LoginSerializer, LogoutSerializer, ResendOTPSerializer)
from .models import VerificationToken, UserProfile
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import  NotFound
from django.conf import settings
from django.urls import reverse
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import send_mail
from django.utils import timezone
from django.shortcuts import redirect
from django.utils.encoding import force_bytes
import uuid
from django.contrib.auth import get_user_model




User = get_user_model()
class UserRegister(APIView):
    serializer_class = UserSerializers
    def post(self, request):
        serializer = UserSerializers(data=request.data, context={'request': request})

        if serializer.is_valid(raise_exception=True):
            email = serializer.validated_data['email']
            username = serializer.validated_data['username']
            resend = request.query_params.get('resend') == 'true'
            purpose = VerificationToken.Choices.REGISTRATION

            try:
                user = User.objects.get(email=email)
                if user.is_active:
                    return Response({"message": "User already registered and active."}, status=status.HTTP_400_BAD_REQUEST)
                elif resend:
                    # Delete old expired tokens
                    VerificationToken.objects.filter(user=user, is_used=False).exclude(expires_at__gte=timezone.now()).delete()

                    # Create a new verification token
                    token = VerificationToken.objects.create(user=user, purpose=purpose)
                    uidb64 = urlsafe_base64_encode(force_bytes(user.pk))

                    verification_link = request.build_absolute_uri(reverse('verify-otp', kwargs={'uidb64': uidb64, 'token': token.token}))
                    send_mail(
                        'Verify Your Account (New OTP)',
                        f'Click the following link within 10 minutes to verify your account: {verification_link}',
                        settings.EMAIL_HOST_USER,
                        [user.email],
                        fail_silently=False
                    )
                    return Response({"message": "New verification link sent."}, status=status.HTTP_200_OK)
                else:
                    return Response({"message": "User already registered but not activated. Please use resend=true query parameter."}, status=status.HTTP_400_BAD_REQUEST)

            except User.DoesNotExist:
                user = serializer.save()
                user.is_active = False
                user.save()

                # Create a verification token
                token = VerificationToken.objects.create(user=user, purpose=purpose)
                uidb64 = urlsafe_base64_encode(force_bytes(user.pk))

                verification_link = request.build_absolute_uri(reverse('verify-otp', kwargs={'uidb64': uidb64, 'token': token.token}))
                send_mail(
                    'Verify Your Account',
                    f'Click the following link within 10 minutes to verify your account: {verification_link}',
                    settings.EMAIL_HOST_USER,
                    [user.email],
                    fail_silently=False
                )
                return Response({"message": "Registration Successful. Please verify your email."}, status=status.HTTP_201_CREATED)
            
signup = UserRegister.as_view()


class ResendOTPView(APIView):
    serializer_class = ResendOTPSerializer
    

    def post(self, request):
        serializer = self.serializer_class(data=request.data)

        if serializer.is_valid(raise_exception=True):
            email = serializer.validated_data['email']
            purpose = VerificationToken.Choices.REGISTERATION
            print(f"email: {email}")
            try:
                # ✅ Corrected line
                user = User.objects.get(email=email)

                # Delete expired tokens
                VerificationToken.objects.filter(
                    user=user,
                    is_used=False
                ).exclude(
                    expires_at__gte=timezone.now()
                ).delete()

                # Create a new token
                token = VerificationToken.objects.create(user=user, purpose=purpose)
                uidb64 = urlsafe_base64_encode(force_bytes(user.pk))

                verification_link = request.build_absolute_uri(
                    reverse('verify-otp', kwargs={'uidb64': uidb64, 'token': token.token})
                )

                send_mail(
                    'Verify Your Account (New OTP)',
                    f'Click the following link within 10 minutes to verify your account: {verification_link}',
                    settings.EMAIL_HOST_USER,
                    [user.email],
                    fail_silently=False
                )

                return Response(
                    {"message": "New verification link sent successfully."},
                    status=status.HTTP_200_OK
                )

            except User.DoesNotExist:
                return Response(
                    {"message": "User not found."},
                    status=status.HTTP_404_NOT_FOUND
                )

resend_otp = ResendOTPView.as_view()



class VerifyOTPView(APIView):
    def get(self, request, uidb64, token):
        try:
            decoded_uid = urlsafe_base64_decode(uidb64).decode()
            user = User.objects.get(pk=decoded_uid)
            verification_token = VerificationToken.objects.filter(user=user, token=token, is_used=False).latest('created_at')

            if verification_token.is_expired():
                user.delete()
                return Response({"message": "OTP has expired."}, status=status.HTTP_400_BAD_REQUEST)

            user.is_active = True
            user.save()

            verification_token.is_used = True
            verification_token.save()

            vercel_url = getattr(settings, "VERCEL_APP_URL", None)
            if not vercel_url:
                return Response({"message": "Redirect URL is missing."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            redirect_url = f"{vercel_url}/?verified=true&email={user.email}"
            return redirect(redirect_url)

        except (User.DoesNotExist, VerificationToken.DoesNotExist, ValueError):
            return Response({"message": "Invalid or expired OTP."}, status=status.HTTP_400_BAD_REQUEST)



class LoginView(APIView):
    serializer_class = LoginSerializer
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            refresh = RefreshToken.for_user(user)
            access_token = refresh.access_token

            try:
                user_profile = user.userprofile
                profile_image = request.build_absolute_uri(user_profile.profile_image.url) if user_profile.profile_image else None
            except UserProfile.DoesNotExist:
                profile_image = None

            return Response({
                'refresh': str(refresh),
                'access': str(access_token),
                'data': {
                    'username': user.username,
                    'first_name':user.first_name,
                    'last_name':user.last_name,
                    'profile_image': request.build_absolute_uri(profile_image) if profile_image else None,
                }
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



class ResendOTPView(APIView):
    serializer_class = ResendOTPSerializer
    
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        
        if serializer.is_valid(raise_exception=True):
            email = serializer.validated_data['email']
            purpose = VerificationToken.Choices.REGISTRATION
            
            try:
                user = User.objects.get(email=email)
                
                
                VerificationToken.objects.filter(
                    user=user, 
                    is_used=False
                ).exclude(
                    expires_at__gte=timezone.now()
                ).delete()
                
                # Create a new verification token
                token = VerificationToken.objects.create(user=user, purpose=purpose)
                uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
                
                verification_link = request.build_absolute_uri(
                    reverse('verify-otp', kwargs={'uidb64': uidb64, 'token': token.token})
                )
                
                send_mail(
                    'Verify Your Account (New OTP)',
                    f'Click the following link within 10 minutes to verify your account: {verification_link}',
                    settings.EMAIL_HOST_USER,
                    [user.email],
                    fail_silently=False
                )
                
                return Response(
                    {"message": "New verification link sent successfully."}, 
                    status=status.HTTP_200_OK
                )
                
            except User.DoesNotExist:
                return Response(
                    {"message": "User not found."}, 
                    status=status.HTTP_404_NOT_FOUND
                )

resend_otp = ResendOTPView.as_view()


class UpdateView(APIView):
    serializer_class = UpdateSerializers
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
        purpose = VerificationToken.Choices.PASSWORD_RESET  # Now correctly uses "PR"

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({"error": "User with this email does not exist."}, status=status.HTTP_404_NOT_FOUND)

        # Delete any existing password reset tokens for the user
        VerificationToken.objects.filter(
            user=user, 
            purpose=purpose, 
            is_used=False, 
            expires_at__gt=timezone.now()
        ).delete()

        otp_instance = VerificationToken.objects.create(user=user, purpose=purpose)
        
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
            return Response(
                {"error": "Failed to send email. Please try again later."}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            
            
            
            
class ResetPasswordView(generics.CreateAPIView):
    serializer_class = ResetPasswordSerializer
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        otp = serializer.validated_data['otp']
        new_password = serializer.validated_data['new_password']

        try:
            otp_instance = VerificationToken.objects.get(
                otp=otp, 
                purpose=VerificationToken.Choices.PASSWORD_RESET,  # Using the correct constant
                is_used=False,
                expires_at__gt=timezone.now()
            )

            user = otp_instance.user
            user.set_password(new_password)
            user.save()

            otp_instance.is_used = True
            otp_instance.save()

            return Response({"message": "Password reset successfully."}, status=status.HTTP_200_OK)
        except VerificationToken.DoesNotExist:
            return Response({"error": "Invalid or expired OTP."}, status=status.HTTP_400_BAD_REQUEST)
        
        
        
        
        
class LogoutView(APIView):
    serializer_class = LogoutSerializer
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
