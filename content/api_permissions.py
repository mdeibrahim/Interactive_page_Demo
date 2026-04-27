from rest_framework.permissions import BasePermission

from .models import UserProfile, UserRole


class IsStudent(BasePermission):
    message = 'Student role required.'

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        profile, _ = UserProfile.objects.get_or_create(
            user=request.user,
            defaults={'role': UserRole.STUDENT},
        )
        return profile.role == UserRole.STUDENT
