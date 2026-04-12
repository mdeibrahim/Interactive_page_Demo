import json
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST, require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils.text import slugify
from django.db.models import Count
from .models import Category, SubCategory, Subject, AccordionSection, InteractiveContent


# ─────────────────────────────────────────────────────────
#   PAGE VIEWS
# ─────────────────────────────────────────────────────────

def home(request):
    """Home page — list all categories"""
    categories = Category.objects.prefetch_related('subcategories__subjects').all()
    return render(request, 'content/home.html', {'categories': categories})


def category_detail(request, cat_slug):
    """List subcategories under a category"""
    category = get_object_or_404(Category, slug=cat_slug)
    subcategories = category.subcategories.prefetch_related('subjects').all()
    return render(request, 'content/category_detail.html', {
        'category': category,
        'subcategories': subcategories,
    })


def subcategory_detail(request, cat_slug, subcat_slug):
    """List subjects under a subcategory"""
    category = get_object_or_404(Category, slug=cat_slug)
    subcategory = get_object_or_404(SubCategory, category=category, slug=subcat_slug)
    subjects = subcategory.subjects.all()
    return render(request, 'content/subcategory_detail.html', {
        'category': category,
        'subcategory': subcategory,
        'subjects': subjects,
    })


def subject_detail(request, cat_slug, subcat_slug, subject_slug):
    """The main details/teaching page"""
    category = get_object_or_404(Category, slug=cat_slug)
    subcategory = get_object_or_404(SubCategory, category=category, slug=subcat_slug)
    subject = get_object_or_404(Subject, subcategory=subcategory, slug=subject_slug)
    accordion_sections = subject.accordion_sections.all()
    interactive_contents = subject.interactive_contents.all()
    return render(request, 'content/subject_detail.html', {
        'category': category,
        'subcategory': subcategory,
        'subject': subject,
        'accordion_sections': accordion_sections,
        'interactive_contents': interactive_contents,
    })


def subject_editor(request, subject_id):
    """Frontend rich-text editor for a subject"""
    subject = get_object_or_404(Subject, id=subject_id)
    category = subject.subcategory.category
    subcategory = subject.subcategory
    accordion_sections = subject.accordion_sections.all()
    interactive_contents = subject.interactive_contents.all()
    return render(request, 'content/subject_editor.html', {
        'subject': subject,
        'category': category,
        'subcategory': subcategory,
        'accordion_sections': accordion_sections,
        'interactive_contents': interactive_contents,
    })


# ─────────────────────────────────────────────────────────
#   AJAX API: READ
# ─────────────────────────────────────────────────────────

@require_GET
def get_interactive_content(request, content_id):
    """AJAX endpoint — returns JSON data for a modal popup"""
    content = get_object_or_404(InteractiveContent, id=content_id)
    return JsonResponse(_serialize_ic(content))


@require_GET
def api_subject(request, subject_id):
    """Return full subject data as JSON"""
    subject = get_object_or_404(Subject, id=subject_id)
    return JsonResponse({
        'id': subject.id,
        'title': subject.title,
        'slug': subject.slug,
        'body_content': subject.body_content,
        'updated_at': subject.updated_at.isoformat(),
        'accordion_sections': [
            {
                'id': s.id,
                'title': s.title,
                'content': s.content,
                'order': s.order,
                'is_open_by_default': s.is_open_by_default,
            }
            for s in subject.accordion_sections.all()
        ],
        'interactive_contents': [
            _serialize_ic(ic) for ic in subject.interactive_contents.all()
        ],
    })


# ─────────────────────────────────────────────────────────
#   AJAX API: SUBJECT SAVE
# ─────────────────────────────────────────────────────────

@csrf_exempt
@require_http_methods(["POST"])
def api_subject_save(request, subject_id):
    """Save subject body_content and title (from frontend editor)"""
    subject = get_object_or_404(Subject, id=subject_id)
    try:
        payload = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    if 'title' in payload:
        subject.title = payload['title'].strip() or subject.title
    if 'body_content' in payload:
        subject.body_content = payload['body_content']
    subject.save()
    return JsonResponse({'ok': True, 'updated_at': subject.updated_at.isoformat()})


# ─────────────────────────────────────────────────────────
#   AJAX API: INTERACTIVE CONTENT CRUD
# ─────────────────────────────────────────────────────────

@csrf_exempt
@require_http_methods(["POST"])
def api_ic_create(request, subject_id):
    """Create a new InteractiveContent item"""
    subject = get_object_or_404(Subject, id=subject_id)
    # Handle multipart (file uploads) or JSON
    if request.content_type and 'multipart' in request.content_type:
        data = request.POST
        files = request.FILES
    else:
        try:
            data = json.loads(request.body)
        except Exception:
            return JsonResponse({'error': 'Invalid body'}, status=400)
        files = {}

    content_type = data.get('content_type', 'text')
    title = data.get('title', 'Untitled')

    ic = InteractiveContent(subject=subject, content_type=content_type, title=title)

    if content_type == 'text':
        ic.text_content = data.get('text_content', '')
    elif content_type == 'image' and 'image' in files:
        ic.image = files['image']
    elif content_type == 'audio' and 'audio' in files:
        ic.audio = files['audio']
    elif content_type == 'video' and 'video' in files:
        ic.video = files['video']
    elif content_type == 'youtube':
        ic.youtube_url = data.get('youtube_url', '')
    ic.save()

    return JsonResponse({'ok': True, 'ic': _serialize_ic(ic)}, status=201)


@csrf_exempt
@require_http_methods(["POST"])
def api_ic_update(request, ic_id):
    """Update an existing InteractiveContent item"""
    ic = get_object_or_404(InteractiveContent, id=ic_id)

    if request.content_type and 'multipart' in request.content_type:
        data = request.POST
        files = request.FILES
    else:
        try:
            data = json.loads(request.body)
        except Exception:
            return JsonResponse({'error': 'Invalid body'}, status=400)
        files = {}

    if 'content_type' in data:
        ic.content_type = data['content_type']
    if 'title' in data:
        ic.title = data['title']
    if 'text_content' in data:
        ic.text_content = data['text_content']
    if 'youtube_url' in data:
        ic.youtube_url = data['youtube_url']
    if 'image' in files:
        ic.image = files['image']
    if 'audio' in files:
        ic.audio = files['audio']
    if 'video' in files:
        ic.video = files['video']
    ic.save()

    return JsonResponse({'ok': True, 'ic': _serialize_ic(ic)})


@csrf_exempt
@require_http_methods(["DELETE", "POST"])
def api_ic_delete(request, ic_id):
    """Delete an InteractiveContent item"""
    ic = get_object_or_404(InteractiveContent, id=ic_id)
    ic.delete()
    return JsonResponse({'ok': True})


# ─────────────────────────────────────────────────────────
#   AJAX API: ACCORDION CRUD
# ─────────────────────────────────────────────────────────

@csrf_exempt
@require_http_methods(["POST"])
def api_accordion_create(request, subject_id):
    """Create accordion section"""
    subject = get_object_or_404(Subject, id=subject_id)
    try:
        data = json.loads(request.body)
    except Exception:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    section = AccordionSection.objects.create(
        subject=subject,
        title=data.get('title', 'New Section'),
        content=data.get('content', ''),
        order=data.get('order', subject.accordion_sections.count()),
        is_open_by_default=data.get('is_open_by_default', False),
    )
    return JsonResponse({'ok': True, 'section': _serialize_section(section)}, status=201)


@csrf_exempt
@require_http_methods(["POST"])
def api_accordion_update(request, section_id):
    """Update accordion section"""
    section = get_object_or_404(AccordionSection, id=section_id)
    try:
        data = json.loads(request.body)
    except Exception:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    if 'title' in data:
        section.title = data['title']
    if 'content' in data:
        section.content = data['content']
    if 'order' in data:
        section.order = data['order']
    if 'is_open_by_default' in data:
        section.is_open_by_default = data['is_open_by_default']
    section.save()
    return JsonResponse({'ok': True, 'section': _serialize_section(section)})


@csrf_exempt
@require_http_methods(["DELETE", "POST"])
def api_accordion_delete(request, section_id):
    """Delete accordion section"""
    section = get_object_or_404(AccordionSection, id=section_id)
    section.delete()
    return JsonResponse({'ok': True})


# ─────────────────────────────────────────────────────────
#   HELPERS
# ─────────────────────────────────────────────────────────

def _serialize_ic(content):
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
