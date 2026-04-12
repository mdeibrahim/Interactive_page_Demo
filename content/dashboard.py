from django.views.decorators.http import require_http_methods
from django.shortcuts import render, redirect
from django.db.models import Count
from django.contrib import admin
from content.models import Category, SubCategory, Subject, AccordionSection, InteractiveContent
from django.contrib.auth.models import User


@require_http_methods(["GET"])
def admin_dashboard(request):
    """
    Admin dashboard with overview statistics of the teaching platform.
    """
    stats = {
        'categories_count': Category.objects.count(),
        'subcategories_count': SubCategory.objects.count(),
        'subjects_count': Subject.objects.count(),
        'accordion_sections_count': AccordionSection.objects.count(),
        'interactive_contents_count': InteractiveContent.objects.count(),
        'total_users': User.objects.count(),
        'staff_users': User.objects.filter(is_staff=True).count(),
    }
    
    # Get category breakdown with subject counts
    categories_with_counts = Category.objects.annotate(
        subject_count=Count('subcategories__subjects')
    ).values('name', 'subject_count').order_by('-subject_count')
    
    # Get latest subjects
    latest_subjects = Subject.objects.select_related('subcategory__category').order_by('-updated_at')[:5]
    
    # Get latest interactive contents
    latest_contents = InteractiveContent.objects.select_related('subject').order_by('-created_at')[:5]
    
    # Get content types distribution
    content_types_dist = InteractiveContent.objects.values('content_type').annotate(
        count=Count('id')
    ).order_by('-count')
    
    context = {
        **admin.site.each_context(request),
        'stats': stats,
        'categories_with_counts': categories_with_counts,
        'latest_subjects': latest_subjects,
        'latest_contents': latest_contents,
        'content_types_dist': content_types_dist,
        'title': 'Dashboard',
        'subtitle': None,
    }

    request.current_app = admin.site.name
    return render(request, 'admin/dashboard.html', context)


@require_http_methods(["GET"])
def admin_root_redirect(request):
    return redirect('admin_dashboard')
