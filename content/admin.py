from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from unfold.admin import ModelAdmin, TabularInline, StackedInline
from .models import Category, SubCategory, Subject, AccordionSection, InteractiveContent


class SubCategoryInline(TabularInline):
    model = SubCategory
    extra = 0
    show_change_link = True
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Category)
class CategoryAdmin(ModelAdmin):
    list_display = ('name', 'slug', 'subcategory_count', 'created_at')
    list_filter = ('created_at',)
    date_hierarchy = 'created_at'
    list_per_page = 25
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name', 'slug', 'description')
    inlines = [SubCategoryInline]

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.prefetch_related('subcategories')

    def subcategory_count(self, obj):
        return obj.subcategories.count()
    subcategory_count.short_description = 'Sub Categories'


@admin.register(SubCategory)
class SubCategoryAdmin(ModelAdmin):
    list_display = ('name', 'category', 'slug', 'subject_count', 'created_at')
    list_select_related = ('category',)
    date_hierarchy = 'created_at'
    list_per_page = 25
    prepopulated_fields = {'slug': ('name',)}
    list_filter = ('category', 'created_at')
    search_fields = ('name', 'slug', 'description', 'category__name')

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.select_related('category').prefetch_related('subjects')

    def subject_count(self, obj):
        return obj.subjects.count()
    subject_count.short_description = 'Subjects'


class AccordionSectionInline(StackedInline):
    model = AccordionSection
    extra = 0
    show_change_link = True
    fields = ('title', 'content', 'order', 'is_open_by_default')


class InteractiveContentInline(TabularInline):
    model = InteractiveContent
    extra = 0
    show_change_link = True
    fields = ('title', 'content_type', 'text_content', 'image', 'audio', 'video', 'youtube_url', 'preview')
    readonly_fields = ('id',)

    def preview(self, obj):
        if not obj.pk:
            return 'Save to preview'
        return InteractiveContentAdmin.preview(self, obj)
    preview.short_description = 'Preview'


@admin.register(Subject)
class SubjectAdmin(ModelAdmin):
    list_display = ('title', 'subcategory', 'category_name', 'content_count', 'updated_at', 'edit_contents_link')
    list_select_related = ('subcategory', 'subcategory__category')
    date_hierarchy = 'updated_at'
    list_per_page = 25
    prepopulated_fields = {'slug': ('title',)}
    list_filter = ('subcategory__category', 'subcategory', 'updated_at')
    search_fields = ('title', 'slug', 'body_content', 'subcategory__name', 'subcategory__category__name')
    autocomplete_fields = ('subcategory',)
    inlines = [AccordionSectionInline, InteractiveContentInline]
    save_as = True

    fieldsets = (
        ('Basic Info', {
            'fields': ('subcategory', 'title', 'slug')
        }),
        ('Body Content', {
            'fields': ('body_content',),
            'description': (
                'Use HTML. To add an interactive highlight link, use: '
                '<code>&lt;span class="highlight-link" data-content-id="ID"&gt;your text&lt;/span&gt;</code> '
                'where ID is the InteractiveContent ID.'
            )
        }),
    )

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.select_related('subcategory', 'subcategory__category').prefetch_related('interactive_contents')

    def category_name(self, obj):
        return obj.subcategory.category.name
    category_name.short_description = 'Category'
    category_name.admin_order_field = 'subcategory__category__name'

    def content_count(self, obj):
        return obj.interactive_contents.count()
    content_count.short_description = 'Interactive Items'

    def edit_contents_link(self, obj):
        url = f"{reverse('admin:content_interactivecontent_changelist')}?subject__id__exact={obj.id}"
        return format_html('<a href="{}">Manage Items</a>', url)
    edit_contents_link.short_description = 'Interactive Content'


@admin.register(AccordionSection)
class AccordionSectionAdmin(ModelAdmin):
    list_display = ('title', 'subject', 'subject_category', 'order', 'is_open_by_default')
    list_select_related = ('subject', 'subject__subcategory', 'subject__subcategory__category')
    list_editable = ('order', 'is_open_by_default')
    list_filter = ('subject__subcategory__category', 'is_open_by_default')
    search_fields = ('title', 'content', 'subject__title')
    autocomplete_fields = ('subject',)
    list_per_page = 30

    def subject_category(self, obj):
        return obj.subject.subcategory.category.name
    subject_category.short_description = 'Category'
    subject_category.admin_order_field = 'subject__subcategory__category__name'


@admin.register(InteractiveContent)
class InteractiveContentAdmin(ModelAdmin):
    list_display = ('id', 'title', 'content_type', 'subject', 'subject_category', 'preview', 'created_at')
    list_select_related = ('subject', 'subject__subcategory', 'subject__subcategory__category')
    list_filter = ('content_type', 'subject__subcategory__category', 'created_at')
    search_fields = ('title', 'text_content', 'youtube_url', 'subject__title', 'subject__subcategory__name')
    autocomplete_fields = ('subject',)
    date_hierarchy = 'created_at'
    list_per_page = 25
    readonly_fields = ('id', 'preview')

    fieldsets = (
        ('Basic', {
            'fields': ('id', 'subject', 'title', 'content_type')
        }),
        ('Text Content', {
            'fields': ('text_content',),
            'classes': ('collapse',),
        }),
        ('Media Files', {
            'fields': ('image', 'audio', 'video'),
            'classes': ('collapse',),
        }),
        ('YouTube', {
            'fields': ('youtube_url',),
            'classes': ('collapse',),
        }),
        ('Preview', {
            'fields': ('preview',),
        }),
    )

    def subject_category(self, obj):
        return obj.subject.subcategory.category.name
    subject_category.short_description = 'Category'
    subject_category.admin_order_field = 'subject__subcategory__category__name'

    def preview(self, obj):
        if obj.content_type == 'image' and obj.image:
            return format_html('<img src="{}" style="max-height:100px;max-width:200px;border-radius:6px;" />', obj.image.url)
        if obj.content_type == 'audio' and obj.audio:
            return format_html('<audio controls style="max-width:300px;"><source src="{}"></audio>', obj.audio.url)
        if obj.content_type == 'video' and obj.video:
            return format_html('<video controls style="max-height:100px;max-width:200px;"><source src="{}"></video>', obj.video.url)
        if obj.content_type == 'youtube' and obj.youtube_url:
            return format_html('<a href="{}" target="_blank">▶ Open YouTube</a>', obj.youtube_url)
        if obj.content_type == 'text' and obj.text_content:
            return format_html('<div style="max-width:300px;overflow:hidden;font-size:12px;">{}</div>', obj.text_content[:200])
        return '—'
    preview.short_description = 'Preview'


# Customize admin site
admin.site.site_header = "Interactive Teaching Platform"
admin.site.site_title = "Teaching Platform Admin"
admin.site.index_title = "Content Management"
