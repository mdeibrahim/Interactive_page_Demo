from django.contrib import admin
from django.utils.html import format_html
from .models import Category, SubCategory, Subject, AccordionSection, InteractiveContent


class SubCategoryInline(admin.TabularInline):
    model = SubCategory
    extra = 1
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'subcategory_count', 'created_at')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name',)
    inlines = [SubCategoryInline]

    def subcategory_count(self, obj):
        return obj.subcategories.count()
    subcategory_count.short_description = 'Sub Categories'


@admin.register(SubCategory)
class SubCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'slug', 'subject_count', 'created_at')
    prepopulated_fields = {'slug': ('name',)}
    list_filter = ('category',)
    search_fields = ('name', 'category__name')

    def subject_count(self, obj):
        return obj.subjects.count()
    subject_count.short_description = 'Subjects'


class AccordionSectionInline(admin.StackedInline):
    model = AccordionSection
    extra = 1
    fields = ('title', 'content', 'order', 'is_open_by_default')


class InteractiveContentInline(admin.TabularInline):
    model = InteractiveContent
    extra = 1
    fields = ('title', 'content_type', 'text_content', 'image', 'audio', 'video', 'youtube_url')
    readonly_fields = ('id',)


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ('title', 'subcategory', 'category_name', 'content_count', 'updated_at')
    prepopulated_fields = {'slug': ('title',)}
    list_filter = ('subcategory__category', 'subcategory')
    search_fields = ('title', 'subcategory__name')
    inlines = [AccordionSectionInline, InteractiveContentInline]

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

    def category_name(self, obj):
        return obj.subcategory.category.name
    category_name.short_description = 'Category'

    def content_count(self, obj):
        return obj.interactive_contents.count()
    content_count.short_description = 'Interactive Items'


@admin.register(AccordionSection)
class AccordionSectionAdmin(admin.ModelAdmin):
    list_display = ('title', 'subject', 'order', 'is_open_by_default')
    list_filter = ('subject__subcategory__category',)
    search_fields = ('title', 'subject__title')


@admin.register(InteractiveContent)
class InteractiveContentAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'content_type', 'subject', 'preview', 'created_at')
    list_filter = ('content_type', 'subject__subcategory__category')
    search_fields = ('title', 'subject__title')
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
