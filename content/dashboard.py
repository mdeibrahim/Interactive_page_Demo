from django.contrib import admin
from django.contrib.auth.models import User
from django.db.models import Count
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from django.apps import apps
from django.urls import reverse
from django.urls.exceptions import NoReverseMatch

from content.models import Course, Module


@require_http_methods(["GET"])
def admin_dashboard(request):
    """
    Admin dashboard with overview statistics and content health insights.
    """
    courses_count = Course.objects.count()
    modules_count = Module.objects.count()

    stats = {
        "courses_count": courses_count,
        "modules_count": modules_count,
        "total_users": User.objects.count(),
        "staff_users": User.objects.filter(is_staff=True).count(),
    }

    courses_without_modules = Course.objects.annotate(
        total_modules=Count("modules")
    ).filter(total_modules=0).count()

    health = {
        "courses_without_modules": courses_without_modules,
    }

    latest_modules = Module.objects.select_related("course").order_by("-created_at")[:8]
    # Build a dynamic list of admin-managed models for the sidebar
    admin_models = []
    try:
        app_config = apps.get_app_config('content')
    except LookupError:
        app_config = None

    if app_config:
        for model in app_config.get_models():
            # only show models that are registered in the admin site
            if model not in admin.site._registry:
                continue
            meta = model._meta
            try:
                changelist = reverse('admin:%s_%s_changelist' % (meta.app_label, meta.model_name))
            except NoReverseMatch:
                changelist = None
            try:
                obj_count = model._default_manager.count()
            except Exception:
                obj_count = None

            label = str(getattr(meta, 'verbose_name_plural', None) or meta.model_name).title()
            admin_models.append({
                'label': label,
                'url': changelist,
                'count': obj_count,
            })

    context = {
        **admin.site.each_context(request),
        "stats": stats,
        "health": health,
        "latest_modules": latest_modules,
        "admin_models": admin_models,
        "title": "Dashboard",
        "subtitle": None,
    }

    request.current_app = admin.site.name
    return render(request, "admin/dashboard.html", context)


@require_http_methods(["GET"])
def admin_root_redirect(request):
    return redirect("admin_dashboard")

