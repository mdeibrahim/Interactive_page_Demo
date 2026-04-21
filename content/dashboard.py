from django.contrib import admin
from django.contrib.auth.models import User
from django.db.models import Count
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from content.models import Category, Course, Module


@require_http_methods(["GET"])
def admin_dashboard(request):
    """
    Admin dashboard with overview statistics and content health insights.
    """
    categories_count = Category.objects.count()
    courses_count = Course.objects.count()
    modules_count = Module.objects.count()

    stats = {
        "categories_count": categories_count,
        "courses_count": courses_count,
        "modules_count": modules_count,
        "total_users": User.objects.count(),
        "staff_users": User.objects.filter(is_staff=True).count(),
    }

    categories_without_courses = Category.objects.annotate(
        total_courses=Count("courses")
    ).filter(total_courses=0).count()

    courses_without_modules = Course.objects.annotate(
        total_modules=Count("modules")
    ).filter(total_modules=0).count()

    health = {
        "categories_without_courses": categories_without_courses,
        "courses_without_modules": courses_without_modules,
    }

    categories_with_counts = Category.objects.annotate(
        module_count=Count("courses__modules")
    ).values("id", "name", "module_count").order_by("-module_count", "name")

    latest_modules = Module.objects.select_related("course__category").order_by("-created_at")[:8]
    context = {
        **admin.site.each_context(request),
        "stats": stats,
        "health": health,
        "categories_with_counts": categories_with_counts,
        "latest_modules": latest_modules,
        "title": "Dashboard",
        "subtitle": None,
    }

    request.current_app = admin.site.name
    return render(request, "admin/dashboard.html", context)


@require_http_methods(["GET"])
def admin_root_redirect(request):
    return redirect("admin_dashboard")

