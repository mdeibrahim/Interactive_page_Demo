import json
import uuid
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.db.models import Avg, Count, OuterRef, Q, Subquery
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST, require_http_methods
from django.views.decorators.csrf import csrf_exempt
from .models import (
    ApprovalStatus,
    CourseCertificate,
    CourseChangeRequest,
    CourseQuiz,
    CourseVideo,
    Category,
    SubCategory,
    Subject,
    SubjectProgress,
    AccordionSection,
    InteractiveContent,
    ModulePurchase,
    UserProfile,
    UserRole,
)
from .forms import (
    CourseChangeRequestForm,
    EmailLoginForm,
    NewCourseAddRequestForm,
    ProfileUpdateForm,
    StudentSignupForm,
    TeacherSignupForm,
)


User = get_user_model()


# ─────────────────────────────────────────────────────────
#   PAGE VIEWS
# ─────────────────────────────────────────────────────────

def home(request):
    """Home page — list all categories"""
    default_detail_slug_sq = SubCategory.objects.filter(category=OuterRef('pk')).order_by('name').values('slug')[:1]
    categories = Category.objects.annotate(
        default_detail_slug=Subquery(default_detail_slug_sq)
    ).prefetch_related('subcategories__subjects').all()
    owned_subcategory_ids = _get_owned_subcategory_ids(request.user)
    return render(request, 'content/home.html', {
        'categories': categories,
        'owned_subcategory_ids': owned_subcategory_ids,
    })


def category_detail(request, cat_slug):
    """Category click should open first details page directly."""
    category = get_object_or_404(Category, slug=cat_slug)
    first_detail = category.subcategories.order_by('name').first()
    if first_detail:
        return redirect('content:category_details', cat_slug=category.slug, subcat_slug=first_detail.slug)

    subcategories = category.subcategories.prefetch_related('subjects').all()
    owned_subcategory_ids = _get_owned_subcategory_ids(request.user)
    return render(request, 'content/category_detail.html', {
        'category': category,
        'subcategories': subcategories,
        'owned_subcategory_ids': owned_subcategory_ids,
    })


def subcategory_detail(request, cat_slug, subcat_slug):
    """List subjects under a subcategory"""
    category = get_object_or_404(Category, slug=cat_slug)
    subcategory = get_object_or_404(SubCategory, category=category, slug=subcat_slug)
    subjects = subcategory.subjects.all()
    has_access = _has_module_access(request.user, subcategory)
    related_subcategories = category.subcategories.exclude(id=subcategory.id).prefetch_related('subjects')[:3]
    owned_subcategory_ids = _get_owned_subcategory_ids(request.user)
    return render(request, 'content/subcategory_detail.html', {
        'category': category,
        'subcategory': subcategory,
        'subjects': subjects,
        'has_access': has_access,
        'related_subcategories': related_subcategories,
        'owned_subcategory_ids': owned_subcategory_ids,
    })


def subject_detail(request, cat_slug, subcat_slug, subject_slug):
    """The main details/teaching page"""
    category = get_object_or_404(Category, slug=cat_slug)
    subcategory = get_object_or_404(SubCategory, category=category, slug=subcat_slug)
    subject = get_object_or_404(Subject, subcategory=subcategory, slug=subject_slug)

    if not _has_module_access(request.user, subcategory):
        return render(request, 'content/module_locked.html', {
            'category': category,
            'subcategory': subcategory,
            'subject': subject,
            'subjects': subcategory.subjects.all(),
        })

    accordion_sections = subject.accordion_sections.all()
    interactive_contents = subject.interactive_contents.all()
    return render(request, 'content/subject_detail.html', {
        'category': category,
        'subcategory': subcategory,
        'subject': subject,
        'accordion_sections': accordion_sections,
        'interactive_contents': interactive_contents,
    })


@login_required
def my_modules(request):
    purchases = ModulePurchase.objects.filter(user=request.user).select_related('subcategory', 'subcategory__category')
    return render(request, 'content/my_modules.html', {'purchases': purchases})


@login_required
def profile_page(request):
    inferred_teacher = request.user.is_staff or request.user.teaching_courses.exists()
    profile, _ = UserProfile.objects.get_or_create(
        user=request.user,
        defaults={'role': UserRole.TEACHER if inferred_teacher else UserRole.STUDENT},
    )
    form = ProfileUpdateForm(request.POST or None, user=request.user, profile=profile)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Profile updated successfully.')
        return redirect('content:profile')
    return render(request, 'content/profile.html', {'form': form, 'profile': profile})


@login_required
def teacher_dashboard(request):
    if not _is_teacher(request.user):
        messages.error(request, 'Only teachers can access this dashboard.')
        return redirect('content:student_dashboard')

    courses = SubCategory.objects.filter(teacher=request.user).select_related('category').prefetch_related('subjects')
    course_cards = []
    total_students = 0
    total_courses = courses.count()

    pending_requests = CourseChangeRequest.objects.filter(teacher=request.user, status=ApprovalStatus.PENDING).count()
    recent_requests = CourseChangeRequest.objects.filter(teacher=request.user).select_related('course')[:8]
    add_course_form = NewCourseAddRequestForm()

    for course in courses:
        purchases = course.purchases.select_related('user').all()
        student_count = purchases.count()
        total_students += student_count
        total_subjects = course.subjects.count()

        avg_progress = 0
        if total_subjects > 0 and student_count > 0:
            progress_values = []
            for purchase in purchases:
                progress_values.append(_calculate_course_progress(purchase.user, course))
            avg_progress = round(sum(progress_values) / len(progress_values), 1) if progress_values else 0

        course_cards.append({
            'course': course,
            'student_count': student_count,
            'total_subjects': total_subjects,
            'video_count': CourseVideo.objects.filter(subject__subcategory=course).count(),
            'quiz_count': CourseQuiz.objects.filter(subject__subcategory=course).count(),
            'avg_progress': avg_progress,
        })

    return render(request, 'content/teacher_dashboard.html', {
        'course_cards': course_cards,
        'total_students': total_students,
        'total_courses': total_courses,
        'pending_requests': pending_requests,
        'recent_requests': recent_requests,
        'add_course_form': add_course_form,
    })


@login_required
def teacher_course_detail(request, course_id):
    if not _is_teacher(request.user):
        messages.error(request, 'Only teachers can access this page.')
        return redirect('content:student_dashboard')

    course = get_object_or_404(SubCategory.objects.select_related('category', 'teacher'), id=course_id, teacher=request.user)
    purchases = course.purchases.select_related('user').order_by('-purchased_at')
    students = []
    for purchase in purchases:
        profile, _ = UserProfile.objects.get_or_create(
            user=purchase.user,
            defaults={'role': UserRole.TEACHER if purchase.user.is_staff else UserRole.STUDENT},
        )
        students.append({
            'user': purchase.user,
            'phone_number': profile.phone_number,
            'purchased_at': purchase.purchased_at,
            'progress': _calculate_course_progress(purchase.user, course),
        })

    videos = CourseVideo.objects.filter(subject__subcategory=course).select_related('subject')
    quizzes = CourseQuiz.objects.filter(subject__subcategory=course).select_related('subject')
    form = CourseChangeRequestForm()

    return render(request, 'content/teacher_course_detail.html', {
        'course': course,
        'students': students,
        'videos': videos,
        'quizzes': quizzes,
        'change_request_form': form,
        'change_requests': course.change_requests.select_related('teacher').all()[:10],
    })


@login_required
@require_POST
def submit_course_change_request(request, course_id):
    if not _is_teacher(request.user):
        messages.error(request, 'Only teachers can submit requests.')
        return redirect('content:student_dashboard')

    course = get_object_or_404(SubCategory, id=course_id, teacher=request.user)
    form = CourseChangeRequestForm(request.POST)
    if form.is_valid():
        change = form.save(commit=False)
        change.teacher = request.user
        change.course = course
        change.status = ApprovalStatus.PENDING
        change.save()
        messages.success(request, 'Change request submitted for admin approval.')
    else:
        messages.error(request, 'Could not submit request. Please check the form fields.')
    return redirect('content:teacher_course_detail', course_id=course.id)


@login_required
@require_POST
def submit_new_course_request(request):
    if not _is_teacher(request.user):
        messages.error(request, 'Only teachers can submit requests.')
        return redirect('content:student_dashboard')

    form = NewCourseAddRequestForm(request.POST)
    if form.is_valid():
        CourseChangeRequest.objects.create(
            teacher=request.user,
            request_type='add',
            course=None,
            requested_category=form.cleaned_data['requested_category'],
            requested_course_name=form.cleaned_data['requested_course_name'].strip(),
            requested_price=form.cleaned_data['requested_price'],
            summary=f"New course request: {form.cleaned_data['requested_course_name'].strip()}",
            details=(form.cleaned_data.get('details') or '').strip(),
            status=ApprovalStatus.PENDING,
        )
        messages.success(request, 'New course add request submitted for admin approval.')
    else:
        messages.error(request, 'Could not submit new course request. Please check the fields.')
    return redirect('content:teacher_dashboard')


@login_required
def student_dashboard(request):
    if _is_teacher(request.user):
        return redirect('content:teacher_dashboard')

    purchases = ModulePurchase.objects.filter(user=request.user).select_related('subcategory', 'subcategory__category')
    purchased_course_ids = set(purchases.values_list('subcategory_id', flat=True))
    available_courses = SubCategory.objects.select_related('category').exclude(id__in=purchased_course_ids)

    purchased_cards = []
    for purchase in purchases:
        progress = _calculate_course_progress(request.user, purchase.subcategory)
        purchased_cards.append({
            'purchase': purchase,
            'progress': progress,
            'is_completed': progress >= 100,
            'certificate': CourseCertificate.objects.filter(user=request.user, subcategory=purchase.subcategory).first(),
        })

    certificates = CourseCertificate.objects.filter(user=request.user).select_related('subcategory', 'subcategory__category')

    return render(request, 'content/student_dashboard.html', {
        'purchased_cards': purchased_cards,
        'available_courses': available_courses[:12],
        'certificates': certificates,
    })


@login_required
@require_POST
def mark_subject_complete(request, subject_id):
    subject = get_object_or_404(Subject.objects.select_related('subcategory', 'subcategory__category'), id=subject_id)
    if not _has_module_access(request.user, subject.subcategory):
        messages.error(request, 'Please purchase or unlock this course first.')
        return redirect('content:category_details', cat_slug=subject.subcategory.category.slug, subcat_slug=subject.subcategory.slug)

    progress, _ = SubjectProgress.objects.get_or_create(user=request.user, subject=subject)
    progress.is_completed = True
    progress.completed_at = timezone.now()
    progress.save()

    messages.success(request, 'Lesson marked as completed.')
    return redirect(
        'content:subject_detail',
        cat_slug=subject.subcategory.category.slug,
        subcat_slug=subject.subcategory.slug,
        subject_slug=subject.slug,
    )


@login_required
@require_POST
def claim_certificate(request, course_id):
    course = get_object_or_404(SubCategory, id=course_id)
    if not _has_module_access(request.user, course):
        messages.error(request, 'You do not have access to this course.')
        return redirect('content:student_dashboard')

    progress = _calculate_course_progress(request.user, course)
    if progress < 100:
        messages.error(request, 'Complete all lessons before claiming certificate.')
        return redirect('content:student_dashboard')

    certificate, created = CourseCertificate.objects.get_or_create(
        user=request.user,
        subcategory=course,
        defaults={'certificate_code': _generate_certificate_code()},
    )
    if created:
        messages.success(request, f'Certificate issued successfully: {certificate.certificate_code}')
    else:
        messages.info(request, f'Certificate already issued: {certificate.certificate_code}')
    return redirect('content:student_dashboard')


def login_selector(request):
    if request.user.is_authenticated:
        return redirect('content:home')
    return render(request, 'registration/login.html')


def signup_selector(request):
    if request.user.is_authenticated:
        return redirect('content:home')
    return render(request, 'registration/signup.html')


def student_login(request):
    return _role_login(request, role=UserRole.STUDENT, template_name='registration/student_login.html')


def teacher_login(request):
    return _role_login(request, role=UserRole.TEACHER, template_name='registration/teacher_login.html')


def student_signup(request):
    return _role_signup(request, role=UserRole.STUDENT, template_name='registration/student_signup.html')


def teacher_signup(request):
    return _role_signup(request, role=UserRole.TEACHER, template_name='registration/teacher_signup.html')


def signup(request):
    return signup_selector(request)


@login_required
@require_POST
def buy_module(request, cat_slug, subcat_slug):
    category = get_object_or_404(Category, slug=cat_slug)
    subcategory = get_object_or_404(SubCategory, category=category, slug=subcat_slug)

    ModulePurchase.objects.get_or_create(user=request.user, subcategory=subcategory)

    if subcategory.is_free:
        messages.success(request, f'"{subcategory.name}" is now added to your account (free course).')
    else:
        messages.success(request, f'Success! You now have access to "{subcategory.name}".')

    next_url = request.POST.get('next')
    if next_url:
        return redirect(next_url)
    return redirect('content:category_details', cat_slug=category.slug, subcat_slug=subcategory.slug)


def subject_editor(request, subject_id):
    """Frontend rich-text editor for a subject"""
    subject = get_object_or_404(Subject, id=subject_id)
    if not request.user.is_authenticated or not request.user.is_staff:
        messages.error(request, 'Only admin/staff can edit content.')
        return redirect(
            'content:subject_detail',
            cat_slug=subject.subcategory.category.slug,
            subcat_slug=subject.subcategory.slug,
            subject_slug=subject.slug,
        )

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
    if not _has_module_access(request.user, content.subject.subcategory):
        return JsonResponse({'error': 'Course access required'}, status=403)
    return JsonResponse(_serialize_ic(content))


@require_GET
def api_subject(request, subject_id):
    """Return full subject data as JSON"""
    subject = get_object_or_404(Subject, id=subject_id)
    if not _has_module_access(request.user, subject.subcategory):
        return JsonResponse({'error': 'Course access required'}, status=403)
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
    unauthorized = _ensure_staff(request)
    if unauthorized:
        return unauthorized

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
    unauthorized = _ensure_staff(request)
    if unauthorized:
        return unauthorized

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
    unauthorized = _ensure_staff(request)
    if unauthorized:
        return unauthorized

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
    unauthorized = _ensure_staff(request)
    if unauthorized:
        return unauthorized

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
    unauthorized = _ensure_staff(request)
    if unauthorized:
        return unauthorized

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
    unauthorized = _ensure_staff(request)
    if unauthorized:
        return unauthorized

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
    unauthorized = _ensure_staff(request)
    if unauthorized:
        return unauthorized

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


def _get_owned_subcategory_ids(user):
    if not user.is_authenticated:
        return set()
    if user.is_staff or user.is_superuser:
        return set(SubCategory.objects.values_list('id', flat=True))
    return set(
        ModulePurchase.objects.filter(user=user).values_list('subcategory_id', flat=True)
    )


def _has_module_access(user, subcategory):
    if subcategory.is_free:
        return True
    if not user.is_authenticated:
        return False
    if user.is_staff or user.is_superuser:
        return True
    return ModulePurchase.objects.filter(user=user, subcategory=subcategory).exists()


def _ensure_staff(request):
    if request.user.is_authenticated and request.user.is_staff:
        return None
    return JsonResponse({'error': 'Only admin/staff can edit content'}, status=403)


def _is_teacher(user):
    if not user.is_authenticated:
        return False
    inferred_teacher = user.is_staff or user.teaching_courses.exists()
    profile, _ = UserProfile.objects.get_or_create(
        user=user,
        defaults={'role': UserRole.TEACHER if inferred_teacher else UserRole.STUDENT},
    )
    return profile.role == UserRole.TEACHER


def _calculate_course_progress(user, subcategory):
    total_subjects = subcategory.subjects.count()
    if total_subjects == 0:
        return 0
    completed = SubjectProgress.objects.filter(
        user=user,
        subject__subcategory=subcategory,
        is_completed=True,
    ).count()
    return round((completed / total_subjects) * 100, 2)


def _generate_certificate_code():
    return f"CERT-{uuid.uuid4().hex[:12].upper()}"


def _role_login(request, role, template_name):
    if request.user.is_authenticated:
        return redirect('content:home')

    form = EmailLoginForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        email = form.cleaned_data['email'].strip().lower()
        password = form.cleaned_data['password']

        matched_users = User.objects.filter(email__iexact=email)
        if matched_users.count() > 1:
            form.add_error('email', 'Multiple accounts found with this email. Please contact support.')
            return render(request, template_name, {'form': form})

        user_obj = matched_users.first()
        if not user_obj:
            form.add_error('email', 'No account found with this email.')
            return render(request, template_name, {'form': form})

        user = authenticate(request=request, username=user_obj.get_username(), password=password)
        if not user:
            form.add_error('password', 'Invalid email or password.')
            return render(request, template_name, {'form': form})

        profile, _ = UserProfile.objects.get_or_create(
            user=user,
            defaults={'role': role},
        )

        if profile.role != role:
            messages.error(request, f'This account is registered as {profile.role}. Please use the correct login page.')
        else:
            login(request, user)
            messages.success(request, f'Welcome back, {user.username}!')
            next_url = request.POST.get('next') or request.GET.get('next')
            if next_url:
                return redirect(next_url)
            if role == UserRole.TEACHER:
                return redirect('content:teacher_dashboard')
            return redirect('content:student_dashboard')

    return render(request, template_name, {'form': form})


def _role_signup(request, role, template_name):
    if request.user.is_authenticated:
        return redirect('content:home')

    form_class = StudentSignupForm if role == UserRole.STUDENT else TeacherSignupForm
    form = form_class(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        form.save_profile(user=user, role=role)

        login(request, user)
        messages.success(request, 'Welcome! Your account has been created successfully.')
        next_url = request.POST.get('next') or request.GET.get('next')
        if next_url:
            return redirect(next_url)
        if role == UserRole.TEACHER:
            return redirect('content:teacher_dashboard')
        return redirect('content:student_dashboard')

    return render(request, template_name, {'form': form})
