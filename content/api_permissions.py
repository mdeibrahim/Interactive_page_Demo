from rest_framework.permissions import BasePermission

from .models import UserRole, UserProfile


class IsTeacher(BasePermission):
    message = 'Teacher role required.'

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        profile, _ = UserProfile.objects.get_or_create(
            user=request.user,
            defaults={'role': UserRole.TEACHER if request.user.is_staff else UserRole.STUDENT},
        )
        return profile.role == UserRole.TEACHER


class IsStudent(BasePermission):
    message = 'Student role required.'

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        profile, _ = UserProfile.objects.get_or_create(
            user=request.user,
            defaults={'role': UserRole.TEACHER if request.user.is_staff else UserRole.STUDENT},
        )
        return profile.role == UserRole.STUDENT
