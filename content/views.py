import uuid
from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Avg, Count, OuterRef, Q, Subquery, Prefetch
from django.contrib import messages
from django.contrib.auth import login
from django.conf import settings
from .utils import send_verification_email
from django.core.cache import cache
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate
from django.utils import timezone
from django.views.decorators.http import require_POST
from .models import (
    ApprovalStatus,
    CourseCertificate,
    CourseChangeRequest,
    CourseQuiz,
    CourseContent,
    Course,
    Module,
    ModulePurchase,
    UserProfile,
    UserRole,
    PaymentInstruction,
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
    """Home page — show courses."""
    courses = Course.objects.prefetch_related('modules').all()
    owned_course_ids = _get_owned_course_ids(request.user)
    return render(request, 'content/home.html', {
        'courses': courses,
        'owned_course_ids': owned_course_ids,
    })



def course_detail(request, course_slug):
    """Course detail page with module list."""
    course = get_object_or_404(Course, slug=course_slug)
    modules_qs = course.modules.prefetch_related(
        Prefetch('course_contents', queryset=CourseContent.objects.order_by('order', 'created_at'))
    ).all()
    modules = list(modules_qs)
    # attach first_content attribute to each module (useful in templates)
    for m in modules:
        contents = list(m.course_contents.all())
        m.first_content = contents[0] if contents else None

    has_access = _has_module_access(request.user, course)
    related_courses = Course.objects.exclude(id=course.id).prefetch_related('modules')[:3]
    owned_course_ids = _get_owned_course_ids(request.user)
    # find first available content to use for "Start" CTA
    first_content = None
    for m in modules:
        if getattr(m, 'first_content', None):
            first_content = m.first_content
            break
    return render(request, 'content/course_detail.html', {
        'course': course,
        'modules': modules,
        'has_access': has_access,
        'related_courses': related_courses,
        'owned_course_ids': owned_course_ids,
        'first_content': first_content,
    })


def play_video(request, course_slug, module_slug, video_id):
    """Play a video inside a module with a right-side video list"""
    course = get_object_or_404(Course, slug=course_slug)
    module = get_object_or_404(Module, course=course, slug=module_slug)
    video = get_object_or_404(CourseContent, id=video_id, module=module)

    has_access = _has_module_access(request.user, course)
    videos = module.course_contents.order_by('order', 'created_at').all()

    # derive embed info for youtube/mp4
    def _get_embed(url):
        from urllib.parse import urlparse, parse_qs
        import re
        if not url:
            return {'type': 'link', 'url': ''}
        host = urlparse(url).netloc.lower()
        if 'youtube.com' in host or 'youtu.be' in host:
            # extract video id
            video_id = None
            try:
                parsed = urlparse(url)
                host2 = (parsed.netloc or '').lower().replace('www.', '')
                if host2 in ('youtube.com', 'm.youtube.com') and parsed.path == '/watch':
                    video_id = (parse_qs(parsed.query).get('v') or [None])[0]
                elif 'shorts' in parsed.path:
                    video_id = parsed.path.split('/shorts/', 1)[1].split('/', 1)[0]
                elif parsed.path.startswith('/embed/'):
                    video_id = parsed.path.split('/embed/', 1)[1].split('/', 1)[0]
                elif host2 == 'youtu.be':
                    video_id = parsed.path.lstrip('/').split('/', 1)[0]
            except Exception:
                video_id = None
            if not video_id:
                m = re.search(r'(?:v=|youtu\.be/|/embed/|/shorts/|/live/)([a-zA-Z0-9_-]{11})', url)
                if m:
                    video_id = m.group(1)
            if video_id:
                return {
                    'type': 'youtube',
                    'video_id': video_id,
                    'embed_url': f'https://www.youtube.com/embed/{video_id}'
                }
            return {'type': 'link', 'url': url}

        if url.lower().endswith('.mp4'):
            return {'type': 'mp4', 'url': url}

        return {'type': 'link', 'url': url}

    # prefer explicit youtube_url field if present
    embed = _get_embed(video.youtube_url or video.video_url)

    return render(request, 'content/video_player.html', {
        'course': course,
        'module': module,
        'video': video,
        'videos': videos,
        'has_access': has_access,
        'embed': embed,
    })

@login_required
def my_modules(request):
    purchases = ModulePurchase.objects.filter(
        user=request.user,
        is_purchased=True,
    ).select_related('course')
    return render(request, 'content/my_modules.html', {'purchases': purchases})


@login_required
def profile_page(request):
    inferred_teacher = request.user.is_staff or request.user.teaching_courses.exists()
    profile, _ = UserProfile.objects.get_or_create(
        user=request.user,
        defaults={'role': UserRole.TEACHER if inferred_teacher else UserRole.STUDENT},
    )
    form = ProfileUpdateForm(request.POST or None, request.FILES or None, user=request.user, profile=profile)
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

    courses = Course.objects.filter(teacher=request.user).prefetch_related('modules')
    course_cards = []
    total_students = 0
    total_courses = courses.count()

    pending_requests = CourseChangeRequest.objects.filter(teacher=request.user, status=ApprovalStatus.PENDING).count()
    recent_requests = CourseChangeRequest.objects.filter(teacher=request.user).select_related('course')[:8]
    add_course_form = NewCourseAddRequestForm()

    for course in courses:
        purchases = course.purchases.filter(is_purchased=True).select_related('user')
        student_count = purchases.count()
        total_students += student_count
        total_modules = course.modules.count()

        course_cards.append({
            'course': course,
            'student_count': student_count,
            'total_subjects': total_modules,
            'content_count': CourseContent.objects.filter(module__course=course).count(),
            'quiz_count': CourseQuiz.objects.filter(module__course=course).count(),
            'avg_progress': 0,
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

    course = get_object_or_404(Course.objects.select_related('teacher'), id=course_id, teacher=request.user)
    purchases = course.purchases.filter(is_purchased=True).select_related('user').order_by('-purchased_at')
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
            'progress': 0,
        })

    contents = CourseContent.objects.filter(module__course=course).select_related('module')
    quizzes = CourseQuiz.objects.filter(module__course=course).select_related('module')
    form = CourseChangeRequestForm()

    return render(request, 'content/teacher_course_detail.html', {
        'course': course,
        'students': students,
        'contents': contents,
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

    course = get_object_or_404(Course, id=course_id, teacher=request.user)
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
def add_course_request(request):
    """Show a full-page form for teachers to request a new course."""
    if not _is_teacher(request.user):
        messages.error(request, 'Only teachers can submit requests.')
        return redirect('content:student_dashboard')

    form = NewCourseAddRequestForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
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
        return redirect('content:teacher_dashboard')

    return render(request, 'content/add_course_request.html', {'form': form})


@login_required
def student_dashboard(request):
    if _is_teacher(request.user):
        return redirect('content:teacher_dashboard')

    purchases = ModulePurchase.objects.filter(
        user=request.user,
        is_purchased=True,
    ).select_related('course')
    purchased_course_ids = set(purchases.values_list('course_id', flat=True))
    available_courses = Course.objects.exclude(id__in=purchased_course_ids)

    purchased_cards = []
    for purchase in purchases:
        progress = 0
        purchased_cards.append({
            'purchase': purchase,
            'progress': progress,
            'is_completed': False,
            'has_access': _has_module_access(request.user, purchase.course),
            'certificate': CourseCertificate.objects.filter(user=request.user, course=purchase.course).first(),
        })

    certificates = CourseCertificate.objects.filter(user=request.user).select_related('course')

    return render(request, 'content/student_dashboard.html', {
        'purchased_cards': purchased_cards,
        'available_courses': available_courses[:12],
        'certificates': certificates,
    })

@login_required
@require_POST
def claim_certificate(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    if not _has_module_access(request.user, course):
        messages.error(request, 'You do not have access to this course.')
        return redirect('content:student_dashboard')

    if not course.modules.exists():
        messages.error(request, 'No modules are available for this course yet.')
        return redirect('content:student_dashboard')

    certificate, created = CourseCertificate.objects.get_or_create(
        user=request.user,
        course=course,
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
def buy_module(request, course_slug):
    course = get_object_or_404(Course, slug=course_slug)

    purchase, created = ModulePurchase.objects.get_or_create(user=request.user, course=course)
    # mark as purchased when user goes through the buy flow
    if not purchase.is_purchased:
        purchase.is_purchased = True
        purchase.save()

    if course.is_free:
        messages.success(request, f'"{course.name}" is now added to your account (free course).')
    else:
        messages.success(request, f'Success! You now have access to "{course.name}".')

    next_url = request.POST.get('next')
    if next_url:
        return redirect(next_url)
    return redirect('content:course_detail', course_slug=course.slug)


@login_required
def start_purchase(request, course_slug):
    """Initialize purchase when user clicks 'এখনই কিনুন'.

    - If course is free (is_free or price == 0): create ModulePurchase and mark is_purchased=True then redirect to course details.
    - If course is paid (>0): create ModulePurchase relation (is_purchased=False) if not exists, then redirect to `course_purchase` page.
    """
    course = get_object_or_404(Course, slug=course_slug)

    purchase, created = ModulePurchase.objects.get_or_create(user=request.user, course=course)

    # Free course: immediately mark as purchased
    is_free = getattr(course, 'is_free', False) or (getattr(course, 'price', 0) == 0)
    if is_free:
        if not purchase.is_purchased:
            purchase.is_purchased = True
            purchase.save()
        messages.success(request, f'"{course.name}" is now added to your account (free course).')
        return redirect('content:course_detail', course_slug=course.slug)

    # Paid course: ensure relation exists but keep is_purchased False, then show purchase page
    if purchase.is_purchased:
        messages.info(request, f'You already have access to "{course.name}".')
        return redirect('content:course_detail', course_slug=course.slug)

    if created:
        purchase.is_purchased = False
        purchase.save()

    return redirect('content:course_purchase', course_slug=course.slug)


@login_required
def course_purchase(request, course_slug):
    """Modern purchase / course detail page showing price and payment options."""
    course = get_object_or_404(Course, slug=course_slug)

    # Render a friendly purchase page. The actual purchase action posts to `buy_module`.
    payment_instructions = PaymentInstruction.objects.order_by('payment_method_name').all()
    return render(request, 'content/course_purchase.html', {
        'course': course,
        'payment_instructions': payment_instructions,
    })

def _get_owned_course_ids(user):
    if not user.is_authenticated:
        return set()
    if user.is_staff or user.is_superuser:
        return set(Course.objects.values_list('id', flat=True))
    return set(
        ModulePurchase.objects.filter(user=user, is_purchased=True).values_list('course_id', flat=True)
    )


def _has_module_access(user, course):
    if course.is_free:
        return True
    if not user.is_authenticated:
        return False
    if user.is_staff or user.is_superuser:
        return True
    return ModulePurchase.objects.filter(
        user=user,
        course=course,
        is_purchased=True,
    ).exists()

def _is_teacher(user):
    if not user.is_authenticated:
        return False
    inferred_teacher = user.is_staff or user.teaching_courses.exists()
    profile, _ = UserProfile.objects.get_or_create(
        user=user,
        defaults={'role': UserRole.TEACHER if inferred_teacher else UserRole.STUDENT},
    )
    return profile.role == UserRole.TEACHER

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

        # Create OTP and redirect to verification
        from django.utils import timezone
        from datetime import timedelta
        from .models import EmailOTP
        import random

        code = f"{random.randint(100000, 999999)}"
        expires = timezone.now() + timedelta(minutes=15)
        EmailOTP.objects.create(user=user, code=code, expires_at=expires)

        # Send verification email (falls back to showing OTP in messages if send fails)
        sent = send_verification_email(user, code)
        if not sent:
            # fallback: surface OTP in messages for debugging or if email send fails
            messages.info(request, f'OTP for verification: {code}')

        request.session['pending_otp_user'] = user.id
        return redirect('content:otp_verify')

    return render(request, template_name, {'form': form})


def otp_verify(request):
    from .forms import OTPForm
    from .models import EmailOTP
    from django.utils import timezone

    user_id = request.session.get('pending_otp_user')
    if not user_id:
        messages.error(request, 'No pending verification found. Please sign up first.')
        return redirect('content:signup')

    user = get_object_or_404(User, id=user_id)

    # Check lockout
    lock_key = f"otp:lockout:{user.id}"
    if cache.get(lock_key):
        messages.error(request, 'Too many failed attempts. Please try again later.')
        return redirect('content:signup')
    form = OTPForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        code = form.cleaned_data['code'].strip()
        otp_qs = EmailOTP.objects.filter(user=user, code=code, is_used=False, expires_at__gte=timezone.now())
        if otp_qs.exists():
            otp = otp_qs.first()
            otp.is_used = True
            otp.save()
            # login user and cleanup
            # reset attempt counter
            attempt_key = f"otp:attempt:{user.id}"
            try:
                cache.delete(attempt_key)
            except Exception:
                pass
            login(request, user)
            request.session.pop('pending_otp_user', None)
            messages.success(request, 'Your account is verified and you are now logged in.')
            profile = UserProfile.objects.get_or_create(user=user)[0]
            if profile.role == UserRole.TEACHER:
                return redirect('content:teacher_dashboard')
            return redirect('content:student_dashboard')
        else:
            # increment attempt counter
            attempt_key = f"otp:attempt:{user.id}"
            try:
                if cache.get(attempt_key) is None:
                    cache.add(attempt_key, 1, timeout=settings.OTP_ATTEMPT_WINDOW)
                else:
                    cache.incr(attempt_key)
            except Exception:
                pass

            # lockout if exceeded
            attempts = cache.get(attempt_key) or 0
            if attempts >= settings.OTP_ATTEMPT_LIMIT:
                lock_key = f"otp:lockout:{user.id}"
                try:
                    cache.set(lock_key, True, timeout=settings.OTP_LOCKOUT_SECONDS)
                except Exception:
                    pass
                messages.error(request, 'Too many failed attempts. Please try again later.')
                return redirect('content:signup')

            form.add_error('code', 'Invalid or expired code.')

    return render(request, 'registration/otp_verify.html', {'form': form, 'email': user.email})


def otp_resend(request):
    from django.utils import timezone
    from datetime import timedelta
    import random
    from .models import EmailOTP

    user_id = request.session.get('pending_otp_user')
    if not user_id:
        messages.error(request, 'No pending verification found.')
        return redirect('content:signup')

    user = get_object_or_404(User, id=user_id)
    code = f"{random.randint(100000, 999999)}"
    expires = timezone.now() + timedelta(minutes=15)
    # rate-limit resends per user
    resend_key = f"otp:resend:{user.id}"
    try:
        cnt = cache.get(resend_key) or 0
        if cnt >= settings.OTP_RESEND_LIMIT:
            messages.error(request, 'Too many resend requests. Please try again later.')
            return redirect('content:otp_verify')

        if cache.get(resend_key) is None:
            cache.add(resend_key, 1, timeout=settings.OTP_RESEND_WINDOW)
        else:
            cache.incr(resend_key)
    except Exception:
        # if cache fails, continue without rate-limiting
        pass

    EmailOTP.objects.create(user=user, code=code, expires_at=expires)
    sent = send_verification_email(user, code)
    if sent:
        messages.success(request, 'A verification code has been sent to your email.')
    else:
        messages.info(request, f'OTP for verification: {code}')
    return redirect('content:otp_verify')
