from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import Category, Course, UserProfile, UserRole


User = get_user_model()


class UserRegisterSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True, min_length=8)
    email = serializers.EmailField(required=True)
    role = serializers.ChoiceField(choices=UserRole.choices, default=UserRole.STUDENT)
    full_name = serializers.CharField(max_length=160)
    phone_number = serializers.CharField(max_length=20)
    student_institution = serializers.CharField(max_length=180, required=False, allow_blank=True)
    student_level = serializers.CharField(max_length=80, required=False, allow_blank=True)
    teacher_institution = serializers.CharField(max_length=180, required=False, allow_blank=True)
    teacher_subject = serializers.CharField(max_length=120, required=False, allow_blank=True)
    teacher_experience_years = serializers.IntegerField(required=False, min_value=0, max_value=60)

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError('Username already exists.')
        return value

    def validate_email(self, value):
        email = (value or '').strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError('Email already exists.')
        return email

    def validate_phone_number(self, value):
        raw_phone = (value or '').strip()
        normalized = raw_phone.replace(' ', '').replace('-', '')
        if normalized.startswith('+'):
            digits = normalized[1:]
        else:
            digits = normalized
        if not digits.isdigit():
            raise serializers.ValidationError('Use only digits, optional +, space or hyphen.')
        if len(digits) < 10 or len(digits) > 15:
            raise serializers.ValidationError('Phone number must be 10 to 15 digits.')
        return normalized

    def validate_full_name(self, value):
        full_name = (value or '').strip()
        if len(full_name) < 3:
            raise serializers.ValidationError('Please provide your full name.')
        return full_name

    def validate(self, attrs):
        role = attrs.get('role', UserRole.STUDENT)
        if role == UserRole.STUDENT:
            if not attrs.get('student_institution', '').strip():
                raise serializers.ValidationError({'student_institution': 'This field is required for students.'})
            if not attrs.get('student_level', '').strip():
                raise serializers.ValidationError({'student_level': 'This field is required for students.'})
        if role == UserRole.TEACHER:
            if not attrs.get('teacher_institution', '').strip():
                raise serializers.ValidationError({'teacher_institution': 'This field is required for teachers.'})
            if not attrs.get('teacher_subject', '').strip():
                raise serializers.ValidationError({'teacher_subject': 'This field is required for teachers.'})
            if attrs.get('teacher_experience_years') is None:
                raise serializers.ValidationError({'teacher_experience_years': 'This field is required for teachers.'})
        return attrs

    def create(self, validated_data):
        role = validated_data.pop('role', UserRole.STUDENT)
        profile_payload = {
            'full_name': validated_data.pop('full_name').strip(),
            'phone_number': validated_data.pop('phone_number'),
            'student_institution': validated_data.pop('student_institution', '').strip(),
            'student_level': validated_data.pop('student_level', '').strip(),
            'teacher_institution': validated_data.pop('teacher_institution', '').strip(),
            'teacher_subject': validated_data.pop('teacher_subject', '').strip(),
            'teacher_experience_years': validated_data.pop('teacher_experience_years', None),
        }
        user = User.objects.create_user(**validated_data)
        UserProfile.objects.create(user=user, role=role, **profile_payload)
        return user


class UserSummarySerializer(serializers.ModelSerializer):
    role = serializers.SerializerMethodField()
    profile = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'role', 'profile')

    def get_role(self, obj):
        inferred_teacher = obj.is_staff or obj.teaching_courses.exists()
        profile, _ = UserProfile.objects.get_or_create(
            user=obj,
            defaults={'role': UserRole.TEACHER if inferred_teacher else UserRole.STUDENT},
        )
        return profile.role

    def get_profile(self, obj):
        inferred_teacher = obj.is_staff or obj.teaching_courses.exists()
        profile, _ = UserProfile.objects.get_or_create(
            user=obj,
            defaults={'role': UserRole.TEACHER if inferred_teacher else UserRole.STUDENT},
        )
        payload = {
            'full_name': profile.full_name,
            'phone_number': profile.phone_number,
        }
        if profile.role == UserRole.STUDENT:
            payload['student_institution'] = profile.student_institution
            payload['student_level'] = profile.student_level
        if profile.role == UserRole.TEACHER:
            payload['teacher_institution'] = profile.teacher_institution
            payload['teacher_subject'] = profile.teacher_subject
            payload['teacher_experience_years'] = profile.teacher_experience_years
        return payload

class DetailSummarySerializer(serializers.ModelSerializer):
    module_count = serializers.IntegerField(source='modules.count', read_only=True)
    is_free = serializers.BooleanField(read_only=True)

    class Meta:
        model = Course
        fields = ('id', 'name', 'slug', 'description', 'price', 'is_free', 'module_count', 'created_at')


class CategorySummarySerializer(serializers.ModelSerializer):
    detail_count = serializers.IntegerField(source='courses.count', read_only=True)
    default_detail_slug = serializers.CharField(read_only=True)

    class Meta:
        model = Category
        fields = ('id', 'name', 'slug', 'description', 'detail_count', 'default_detail_slug', 'created_at')
