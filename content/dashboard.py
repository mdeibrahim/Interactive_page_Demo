from django.contrib import admin
from django.contrib.auth.models import User
from django.db.models import Count
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from content.models import AccordionSection, Category, InteractiveContent, Subject, SubCategory, Module


@require_http_methods(["GET"])
def admin_dashboard(request):
    """
    Admin dashboard with overview statistics and content health insights.
    """
    categories_count = Category.objects.count()
    subcategories_count = SubCategory.objects.count()
    subjects_count = Subject.objects.count()
    accordion_sections_count = AccordionSection.objects.count()
    interactive_contents_count = InteractiveContent.objects.count()
    modules_count = Module.objects.count()

    stats = {
        "categories_count": categories_count,
        "subcategories_count": subcategories_count,
        "subjects_count": subjects_count,
        "accordion_sections_count": accordion_sections_count,
        "interactive_contents_count": interactive_contents_count,
        "modules_count": modules_count,
        "total_users": User.objects.count(),
        "staff_users": User.objects.filter(is_staff=True).count(),
    }

    categories_without_subcategories = Category.objects.annotate(
        total_subcategories=Count("subcategories")
    ).filter(total_subcategories=0).count()

    subcategories_without_subjects = SubCategory.objects.annotate(
        total_subjects=Count("subjects")
    ).filter(total_subjects=0).count()

    subjects_with_interactive = Subject.objects.annotate(
        total_contents=Count("interactive_contents")
    ).exclude(total_contents=0).count()

    subjects_without_interactive = max(subjects_count - subjects_with_interactive, 0)

    subject_coverage = round((subjects_with_interactive / subjects_count) * 100, 1) if subjects_count else 0
    average_interactive_per_subject = (
        round(interactive_contents_count / subjects_count, 2) if subjects_count else 0
    )

    health = {
        "subject_coverage": subject_coverage,
        "average_interactive_per_subject": average_interactive_per_subject,
        "categories_without_subcategories": categories_without_subcategories,
        "subcategories_without_subjects": subcategories_without_subjects,
        "subjects_without_interactive": subjects_without_interactive,
        "subjects_with_interactive": subjects_with_interactive,
    }

    categories_with_counts = Category.objects.annotate(
        subject_count=Count("subcategories__subjects")
    ).values("id", "name", "subject_count").order_by("-subject_count", "name")

    latest_subjects = Subject.objects.select_related("subcategory__category").order_by("-updated_at")[:8]
    latest_contents = InteractiveContent.objects.select_related("subject").order_by("-created_at")[:8]

    top_subjects_by_content = Subject.objects.annotate(
        interactive_total=Count("interactive_contents")
    ).select_related("subcategory__category").order_by("-interactive_total", "title")[:6]

    content_types_dist = list(
        InteractiveContent.objects.values("content_type")
        .annotate(count=Count("id"))
        .order_by("-count", "content_type")
    )

    content_type_label_map = dict(InteractiveContent._meta.get_field("content_type").choices)
    for item in content_types_dist:
        item["label"] = content_type_label_map.get(item["content_type"], item["content_type"])
        item["percentage"] = (
            round((item["count"] / interactive_contents_count) * 100, 1)
            if interactive_contents_count
            else 0
        )

    context = {
        **admin.site.each_context(request),
        "stats": stats,
        "health": health,
        "categories_with_counts": categories_with_counts,
        "latest_subjects": latest_subjects,
        "latest_contents": latest_contents,
        "top_subjects_by_content": top_subjects_by_content,
        "content_types_dist": content_types_dist,
        "title": "Dashboard",
        "subtitle": None,
    }

    request.current_app = admin.site.name
    return render(request, "admin/dashboard.html", context)


@require_http_methods(["GET"])
def admin_root_redirect(request):
    return redirect("admin_dashboard")
