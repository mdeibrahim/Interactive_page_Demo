from django.db import models


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
    name = models.CharField(max_length=255)
    slug = models.SlugField()
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Sub Categories"
        unique_together = ('category', 'slug')
        ordering = ['name']

    def __str__(self):
        return f"{self.category.name} → {self.name}"


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
