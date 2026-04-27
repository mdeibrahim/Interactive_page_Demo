from datetime import datetime, timezone as dt_timezone

from django.contrib.auth import authenticate
from django.contrib.auth import get_user_model
 
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken

from .api_permissions import IsStudent
from .api_serializers import (
    DetailSummarySerializer,
    UserRegisterSerializer,
    UserSummarySerializer,
)
from .models import (
    ModulePurchase,
    StudentDeviceSession,
    Course,
    UserProfile,
    UserRole,
)

User = get_user_model()


def _get_user_role(user):
    profile, _ = UserProfile.objects.get_or_create(
        user=user,
        defaults={'role': UserRole.STUDENT},
    )
    if profile.role != UserRole.STUDENT:
        profile.role = UserRole.STUDENT
        profile.teacher_institution = ''
        profile.teacher_subject = ''
        profile.teacher_experience_years = None
        profile.save(update_fields=['role', 'teacher_institution', 'teacher_subject', 'teacher_experience_years'])
    return profile.role


def _has_detail_access(user, detail):
    if detail.is_free:
        return True
    if not user or not user.is_authenticated:
        return False
    return ModulePurchase.objects.filter(
        user=user,
        course=detail,
        is_purchased=True,
    ).exists()


def _blacklist_by_jti(jti):
    try:
        outstanding = OutstandingToken.objects.get(jti=jti)
    except OutstandingToken.DoesNotExist:
        return
    BlacklistedToken.objects.get_or_create(token=outstanding)


def _enforce_student_device_limit(user, refresh, request):
    StudentDeviceSession.objects.filter(user=user, expires_at__lte=timezone.now()).delete()

    jti = str(refresh.get('jti'))
    if not jti:
        return

    StudentDeviceSession.objects.get_or_create(
        user=user,
        jti=jti,
        defaults={
            'expires_at': datetime.fromtimestamp(int(refresh['exp']), tz=dt_timezone.utc),
            'user_agent': (request.headers.get('User-Agent') or '')[:255],
            'ip_address': request.META.get('REMOTE_ADDR'),
        },
    )

    sessions = StudentDeviceSession.objects.filter(user=user).order_by('created_at')
    while sessions.count() > 2:
        oldest = sessions.first()
        if not oldest:
            break
        _blacklist_by_jti(oldest.jti)
        oldest.delete()
        sessions = StudentDeviceSession.objects.filter(user=user).order_by('created_at')

class RegisterAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = UserRegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        refresh = RefreshToken.for_user(user)
        role = _get_user_role(user)
        refresh['role'] = role
        refresh['username'] = user.username
        access = refresh.access_token
        access['role'] = role
        access['username'] = user.username

        if role == UserRole.STUDENT:
            _enforce_student_device_limit(user, refresh, request)

        return Response(
            {
                'message': 'Registration successful.',
                'user': UserSummarySerializer(user).data,
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(access),
                },
            },
            status=status.HTTP_201_CREATED,
        )


class LoginAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        login_identifier = (
            request.data.get('username')
            or request.data.get('email')
            or request.data.get('login')
            or ''
        )
        password = request.data.get('password', '')
        username = str(login_identifier).strip()

        if '@' in username:
            matched = User.objects.filter(email__iexact=username).first()
            if matched:
                username = matched.get_username()

        user = authenticate(request=request, username=username, password=password)
        if not user:
            return Response({'detail': 'Invalid credentials.'}, status=status.HTTP_401_UNAUTHORIZED)

        refresh = RefreshToken.for_user(user)
        role = _get_user_role(user)
        refresh['role'] = role
        refresh['username'] = user.username
        access = refresh.access_token
        access['role'] = role
        access['username'] = user.username

        if role == UserRole.STUDENT:
            _enforce_student_device_limit(user, refresh, request)

        return Response(
            {
                'message': 'Login successful.',
                'user': UserSummarySerializer(user).data,
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(access),
                },
            }
        )


class RefreshAccessTokenAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = TokenRefreshSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        refresh_raw = request.data.get('refresh')
        if refresh_raw:
            try:
                refresh = RefreshToken(refresh_raw)
                jti = str(refresh.get('jti'))
                if jti:
                    StudentDeviceSession.objects.filter(jti=jti).update(last_seen=timezone.now())
            except TokenError:
                pass

        return Response(serializer.validated_data, status=status.HTTP_200_OK)


class LogoutAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_raw = request.data.get('refresh')
        if not refresh_raw:
            return Response({'detail': 'refresh token is required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            refresh = RefreshToken(refresh_raw)
        except TokenError:
            return Response({'detail': 'Invalid refresh token.'}, status=status.HTTP_400_BAD_REQUEST)

        token_user_id = refresh.get('user_id')
        if token_user_id != request.user.id:
            return Response({'detail': 'Token does not belong to authenticated user.'}, status=status.HTTP_403_FORBIDDEN)

        jti = str(refresh.get('jti'))
        refresh.blacklist()
        if jti:
            StudentDeviceSession.objects.filter(user=request.user, jti=jti).delete()

        return Response({'message': 'Logged out successfully.'}, status=status.HTTP_200_OK)


class MeAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSummarySerializer(request.user).data)


# Category APIs removed — focus on course-centric endpoints


class DetailRetrieveAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, course_slug):
        detail = Course.objects.filter(slug=course_slug).prefetch_related('modules').first()
        if not detail:
            return Response({'detail': 'Details not found.'}, status=status.HTTP_404_NOT_FOUND)

        has_access = _has_detail_access(request.user, detail)

        return Response(
            {
                'detail': DetailSummarySerializer(detail).data,
                'has_access': has_access,
            }
        )


class BuyDetailAPIView(APIView):
    permission_classes = [IsAuthenticated, IsStudent]

    def post(self, request, course_slug):
        detail = Course.objects.filter(slug=course_slug).first()
        if not detail:
            return Response({'detail': 'Details not found.'}, status=status.HTTP_404_NOT_FOUND)

        purchase, _ = ModulePurchase.objects.get_or_create(user=request.user, course=detail)
        if not purchase.is_purchased:
            purchase.is_purchased = True
            purchase.save(update_fields=['is_purchased'])

        return Response(
            {
                'message': 'Access granted.',
                'detail_slug': detail.slug,
            },
            status=status.HTTP_200_OK,
        )


class MyModulesAPIView(APIView):
    permission_classes = [IsAuthenticated, IsStudent]

    def get(self, request):
        purchases = ModulePurchase.objects.filter(
            user=request.user,
            is_purchased=True,
        ).select_related('course')
        data = [
            {
                'id': p.id,
                'detail_name': p.course.name,
                'detail_slug': p.course.slug,
                'price': p.course.price,
                'purchased_at': p.purchased_at,
            }
            for p in purchases
        ]
        return Response(data)
