from django.db import models
from django.contrib.auth import get_user_model


User = get_user_model()


class UserRole(models.TextChoices):
    TEACHER = 'teacher', 'Teacher'
    STUDENT = 'student', 'Student'


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=UserRole.choices, default=UserRole.STUDENT)
    full_name = models.CharField(max_length=160, blank=True, default='')
    phone_number = models.CharField(max_length=20, blank=True, default='')
    student_institution = models.CharField(max_length=180, blank=True, default='')
    student_level = models.CharField(max_length=80, blank=True, default='')
    teacher_institution = models.CharField(max_length=180, blank=True, default='')
    teacher_subject = models.CharField(max_length=120, blank=True, default='')
    teacher_experience_years = models.PositiveSmallIntegerField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['user__username']

    def __str__(self):
        return f"{self.user.username} ({self.role})"


class StudentDeviceSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='student_device_sessions')
    jti = models.CharField(max_length=64, unique=True)
    user_agent = models.CharField(max_length=255, blank=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_seen = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField()

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} device session ({self.jti})"


class Category(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['name']

    def __str__(self):
        return self.name


class SubCategory(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='subcategories')
    teacher = models.ForeignKey(User, on_delete=models.SET_NULL, related_name='teaching_courses', blank=True, null=True)
    name = models.CharField(max_length=255)
    slug = models.SlugField()
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Sub Categories"
        unique_together = ('category', 'slug')
        ordering = ['name']

    def __str__(self):
        return f"{self.category.name} → {self.name}"

    @property
    def is_free(self):
        return self.price <= 0


class Subject(models.Model):
    """A subject (details page) under a subcategory"""
    subcategory = models.ForeignKey(SubCategory, on_delete=models.CASCADE, related_name='subjects')
    title = models.CharField(max_length=500)
    slug = models.SlugField()
    body_content = models.TextField(
        help_text="HTML content. Use <span class='highlight-link' data-content-id='ID'>text</span> to add interactive highlights."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('subcategory', 'slug')
        ordering = ['title']

    def __str__(self):
        return self.title


class AccordionSection(models.Model):
    """Expandable sidebar sections for a subject"""
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='accordion_sections')
    title = models.CharField(max_length=255)
    content = models.TextField(help_text="HTML content for this accordion section")
    order = models.PositiveIntegerField(default=0)
    is_open_by_default = models.BooleanField(default=False)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.subject.title} - {self.title}"


CONTENT_TYPE_CHOICES = [
    ('text', 'Text / Rich HTML'),
    ('image', 'Image'),
    ('audio', 'Audio'),
    ('video', 'Video (Upload)'),
    ('youtube', 'YouTube Video'),
]


class InteractiveContent(models.Model):
    """
    A piece of multimedia content that can be linked to a highlight/click-point
    inside a subject's body content. Opened in a modal on click.
    """
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='interactive_contents')
    title = models.CharField(max_length=255)
    content_type = models.CharField(max_length=20, choices=CONTENT_TYPE_CHOICES)

    # Text content
    text_content = models.TextField(blank=True, help_text="For 'text' type — can include HTML with bold/italic/underline")

    # Media files
    image = models.ImageField(upload_to='interactive/images/', blank=True, null=True)
    audio = models.FileField(upload_to='interactive/audio/', blank=True, null=True)
    video = models.FileField(upload_to='interactive/videos/', blank=True, null=True)

    # YouTube
    youtube_url = models.URLField(blank=True, help_text="Full YouTube URL e.g. https://www.youtube.com/watch?v=...")

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"[{self.get_content_type_display()}] {self.title}"

    def get_youtube_embed_url(self):
        """Convert a YouTube URL (watch/shorts/youtu.be/embed) to embed URL."""
        from urllib.parse import urlparse, parse_qs
        import re

        if not self.youtube_url:
            return ''

        raw_url = self.youtube_url.strip()
        video_id = None

        try:
            parsed = urlparse(raw_url)
            host = (parsed.netloc or '').lower().replace('www.', '')

            # https://youtube.com/watch?v=VIDEO_ID
            if host in ('youtube.com', 'm.youtube.com'):
                if parsed.path == '/watch':
                    video_id = (parse_qs(parsed.query).get('v') or [None])[0]
                elif parsed.path.startswith('/shorts/'):
                    video_id = parsed.path.split('/shorts/', 1)[1].split('/', 1)[0]
                elif parsed.path.startswith('/live/'):
                    video_id = parsed.path.split('/live/', 1)[1].split('/', 1)[0]
                elif parsed.path.startswith('/embed/'):
                    video_id = parsed.path.split('/embed/', 1)[1].split('/', 1)[0]

            # https://youtu.be/VIDEO_ID
            elif host == 'youtu.be':
                video_id = parsed.path.lstrip('/').split('/', 1)[0]
        except Exception:
            video_id = None

        # Fallback regex (supports pasted text/HTML containing a YouTube id)
        if not video_id:
            match = re.search(r'(?:v=|youtu\.be/|/embed/|/shorts/|/live/)([a-zA-Z0-9_-]{11})', raw_url)
            if match:
                video_id = match.group(1)

        if video_id and re.fullmatch(r'[a-zA-Z0-9_-]{11}', video_id):
            return f"https://www.youtube.com/embed/{video_id}"

        return ''


class ModulePurchase(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='module_purchases')
    subcategory = models.ForeignKey(SubCategory, on_delete=models.CASCADE, related_name='purchases')
    purchased_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'subcategory')
        ordering = ['-purchased_at']

    def __str__(self):
        return f"{self.user} purchased {self.subcategory.name}"


class CourseVideo(models.Model):
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='course_videos')
    title = models.CharField(max_length=255)
    video_url = models.URLField()
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'created_at']

    def __str__(self):
        return f"{self.subject.title} - {self.title}"


class CourseQuiz(models.Model):
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='course_quizzes')
    title = models.CharField(max_length=255)
    pass_score = models.PositiveSmallIntegerField(default=50)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.subject.title} - {self.title}"


class CourseQuizQuestion(models.Model):
    quiz = models.ForeignKey(CourseQuiz, on_delete=models.CASCADE, related_name='questions')
    question = models.TextField()
    option_a = models.CharField(max_length=255)
    option_b = models.CharField(max_length=255)
    option_c = models.CharField(max_length=255)
    option_d = models.CharField(max_length=255)
    correct_option = models.CharField(max_length=1, choices=[('A', 'A'), ('B', 'B'), ('C', 'C'), ('D', 'D')])
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return f"{self.quiz.title} Q{self.id}"


class QuizAttempt(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='quiz_attempts')
    quiz = models.ForeignKey(CourseQuiz, on_delete=models.CASCADE, related_name='attempts')
    score = models.PositiveSmallIntegerField(default=0)
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-submitted_at']

    def __str__(self):
        return f"{self.user.username} - {self.quiz.title} ({self.score}%)"


class SubjectProgress(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='subject_progress')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='progress_records')
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'subject')
        ordering = ['-updated_at']

    def __str__(self):
        return f"{self.user.username} - {self.subject.title}"


class CourseCertificate(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='course_certificates')
    subcategory = models.ForeignKey(SubCategory, on_delete=models.CASCADE, related_name='certificates')
    certificate_code = models.CharField(max_length=40, unique=True)
    issued_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'subcategory')
        ordering = ['-issued_at']

    def __str__(self):
        return f"{self.user.username} - {self.subcategory.name} certificate"


class ApprovalStatus(models.TextChoices):
    PENDING = 'pending', 'Pending'
    APPROVED = 'approved', 'Approved'
    REJECTED = 'rejected', 'Rejected'


class CourseChangeRequest(models.Model):
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, related_name='course_change_requests')
    course = models.ForeignKey(SubCategory, on_delete=models.CASCADE, related_name='change_requests', blank=True, null=True)
    requested_category = models.ForeignKey(Category, on_delete=models.SET_NULL, related_name='course_add_requests', blank=True, null=True)
    requested_course_name = models.CharField(max_length=255, blank=True, default='')
    requested_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    request_type = models.CharField(max_length=20, choices=[('add', 'Add'), ('update', 'Update'), ('remove', 'Remove')])
    summary = models.CharField(max_length=255)
    details = models.TextField(blank=True, default='')
    status = models.CharField(max_length=20, choices=ApprovalStatus.choices, default=ApprovalStatus.PENDING)
    admin_note = models.TextField(blank=True, default='')
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, related_name='reviewed_change_requests', blank=True, null=True)
    reviewed_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.course.name} - {self.request_type} ({self.status})"
