from datetime import datetime, timezone as dt_timezone

from django.contrib.auth import authenticate
from django.contrib.auth import get_user_model
from django.db.models import OuterRef, Subquery
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken

from .api_permissions import IsTeacher, IsStudent
from .api_serializers import (
    CategorySummarySerializer,
    DetailSummarySerializer,
    SubjectSummarySerializer,
    UserRegisterSerializer,
    UserSummarySerializer,
)
from .models import (
    AccordionSection,
    Category,
    InteractiveContent,
    ModulePurchase,
    StudentDeviceSession,
    SubCategory,
    Subject,
    UserProfile,
    UserRole,
)

User = get_user_model()


def _get_user_role(user):
    inferred_teacher = user.is_staff or user.teaching_courses.exists()
    profile, _ = UserProfile.objects.get_or_create(
        user=user,
        defaults={'role': UserRole.TEACHER if inferred_teacher else UserRole.STUDENT},
    )
    return profile.role


def _has_detail_access(user, detail):
    if detail.is_free:
        return True
    if not user or not user.is_authenticated:
        return False
    return ModulePurchase.objects.filter(user=user, subcategory=detail).exists()


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


def _serialize_interactive(content):
    return {
        'id': content.id,
        'title': content.title,
        'content_type': content.content_type,
        'text_content': content.text_content,
        'image_url': content.image.url if content.image else None,
        'audio_url': content.audio.url if content.audio else None,
        'video_url': content.video.url if content.video else None,
        'youtube_url': content.youtube_url,
        'youtube_embed_url': content.get_youtube_embed_url(),
    }


def _serialize_section(section):
    return {
        'id': section.id,
        'title': section.title,
        'content': section.content,
        'order': section.order,
        'is_open_by_default': section.is_open_by_default,
    }


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


class CategoryListAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        default_detail_slug_sq = SubCategory.objects.filter(category=OuterRef('pk')).order_by('name').values('slug')[:1]
        categories = Category.objects.annotate(
            default_detail_slug=Subquery(default_detail_slug_sq)
        ).prefetch_related('subcategories').all()
        return Response(CategorySummarySerializer(categories, many=True).data)


class CategoryDetailsListAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, cat_slug):
        category = Category.objects.filter(slug=cat_slug).first()
        if not category:
            return Response({'detail': 'Category not found.'}, status=status.HTTP_404_NOT_FOUND)

        details = category.subcategories.prefetch_related('subjects').all()
        payload = {
            'category': CategorySummarySerializer(category).data,
            'details': DetailSummarySerializer(details, many=True).data,
        }
        return Response(payload)


class DetailRetrieveAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, cat_slug, subcat_slug):
        category = Category.objects.filter(slug=cat_slug).first()
        if not category:
            return Response({'detail': 'Category not found.'}, status=status.HTTP_404_NOT_FOUND)

        detail = SubCategory.objects.filter(category=category, slug=subcat_slug).first()
        if not detail:
            return Response({'detail': 'Details not found.'}, status=status.HTTP_404_NOT_FOUND)

        subjects = detail.subjects.all()
        has_access = _has_detail_access(request.user, detail)

        return Response(
            {
                'category': CategorySummarySerializer(category).data,
                'detail': DetailSummarySerializer(detail).data,
                'has_access': has_access,
                'subjects': SubjectSummarySerializer(subjects, many=True).data,
            }
        )


class SubjectRetrieveAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, cat_slug, subcat_slug, subject_slug):
        category = Category.objects.filter(slug=cat_slug).first()
        if not category:
            return Response({'detail': 'Category not found.'}, status=status.HTTP_404_NOT_FOUND)

        detail = SubCategory.objects.filter(category=category, slug=subcat_slug).first()
        if not detail:
            return Response({'detail': 'Details not found.'}, status=status.HTTP_404_NOT_FOUND)

        subject = Subject.objects.filter(subcategory=detail, slug=subject_slug).first()
        if not subject:
            return Response({'detail': 'Subject not found.'}, status=status.HTTP_404_NOT_FOUND)

        if not _has_detail_access(request.user, detail):
            return Response({'detail': 'Course access required.'}, status=status.HTTP_403_FORBIDDEN)

        sections = AccordionSection.objects.filter(subject=subject)
        interactive = InteractiveContent.objects.filter(subject=subject)

        return Response(
            {
                'id': subject.id,
                'title': subject.title,
                'slug': subject.slug,
                'body_content': subject.body_content,
                'updated_at': subject.updated_at,
                'accordion_sections': [_serialize_section(s) for s in sections],
                'interactive_contents': [_serialize_interactive(ic) for ic in interactive],
            }
        )


class BuyDetailAPIView(APIView):
    permission_classes = [IsAuthenticated, IsStudent]

    def post(self, request, cat_slug, subcat_slug):
        category = Category.objects.filter(slug=cat_slug).first()
        if not category:
            return Response({'detail': 'Category not found.'}, status=status.HTTP_404_NOT_FOUND)

        detail = SubCategory.objects.filter(category=category, slug=subcat_slug).first()
        if not detail:
            return Response({'detail': 'Details not found.'}, status=status.HTTP_404_NOT_FOUND)

        ModulePurchase.objects.get_or_create(user=request.user, subcategory=detail)

        return Response(
            {
                'message': 'Access granted.',
                'detail_slug': detail.slug,
                'category_slug': category.slug,
            },
            status=status.HTTP_200_OK,
        )


class MyModulesAPIView(APIView):
    permission_classes = [IsAuthenticated, IsStudent]

    def get(self, request):
        purchases = ModulePurchase.objects.filter(user=request.user).select_related('subcategory', 'subcategory__category')
        data = [
            {
                'id': p.id,
                'category': p.subcategory.category.name,
                'category_slug': p.subcategory.category.slug,
                'detail_name': p.subcategory.name,
                'detail_slug': p.subcategory.slug,
                'price': p.subcategory.price,
                'purchased_at': p.purchased_at,
            }
            for p in purchases
        ]
        return Response(data)


class TeacherSubjectUpdateAPIView(APIView):
    permission_classes = [IsAuthenticated, IsTeacher]

    def patch(self, request, subject_id):
        subject = Subject.objects.filter(id=subject_id).first()
        if not subject:
            return Response({'detail': 'Subject not found.'}, status=status.HTTP_404_NOT_FOUND)

        title = request.data.get('title')
        body_content = request.data.get('body_content')

        if title is not None:
            title = str(title).strip()
            if title:
                subject.title = title

        if body_content is not None:
            subject.body_content = str(body_content)

        subject.save()
        return Response({'message': 'Subject updated successfully.', 'updated_at': subject.updated_at})
