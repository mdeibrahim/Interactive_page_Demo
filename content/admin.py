from django.contrib import admin
from django.utils import timezone
from unfold.admin import ModelAdmin, TabularInline
from .models import (
    CourseCertificate,
    CourseChangeRequest,
    CourseQuiz,
    CourseQuizQuestion,
    CourseContent,
    Course,
    PaymentInstruction,
    QuizAttempt,
    ModulePurchase,
    Module, UserProfile,
    StudentDeviceSession,
)


class CourseInline(TabularInline):
    model = Course
    extra = 0
    show_change_link = True
    prepopulated_fields = {'slug': ('name',)}
    fields = ('name', 'slug', 'teacher', 'price', 'description')


# Category admin removed — categories removed from models

@admin.register(Course)
class CourseAdmin(ModelAdmin):
    list_display = ('name', 'teacher', 'price', 'created_at')
    list_filter = ('teacher', 'created_at')
    search_fields = ('name', 'slug', 'teacher__username')
    autocomplete_fields = ('teacher',)
    prepopulated_fields = {'slug': ('name',)}
    date_hierarchy = 'created_at'
    list_per_page = 30





@admin.register(ModulePurchase)
class ModulePurchaseAdmin(ModelAdmin):
    list_display = ('id', 'user', 'course', 'module_price', 'purchased_at')
    list_select_related = ('user', 'course')
    list_filter = ('course', 'purchased_at')
    search_fields = ('user__username', 'user__email', 'course__name')
    autocomplete_fields = ('user', 'course')
    date_hierarchy = 'purchased_at'
    list_per_page = 30

    def module_price(self, obj):
        return obj.course.price
    module_price.short_description = 'Price'


@admin.register(UserProfile)
class UserProfileAdmin(ModelAdmin):
    list_display = ('user', 'role', 'full_name', 'phone_number', 'created_at', 'updated_at')
    list_filter = ('role', 'created_at')
    search_fields = ('user__username', 'user__email', 'full_name', 'phone_number')
    autocomplete_fields = ('user',)
    list_per_page = 30
    fieldsets = (
        ('Account', {'fields': ('user', 'role', 'full_name', 'phone_number')}),
        ('Student Fields', {'fields': ('student_institution', 'student_level')}),
        ('Teacher Fields', {'fields': ('teacher_institution', 'teacher_subject', 'teacher_experience_years')}),
        ('Audit', {'fields': ('created_at', 'updated_at')}),
    )
    readonly_fields = ('created_at', 'updated_at')


@admin.register(StudentDeviceSession)
class StudentDeviceSessionAdmin(ModelAdmin):
    list_display = ('user', 'jti', 'ip_address', 'created_at', 'expires_at', 'last_seen')
    search_fields = ('user__username', 'jti', 'ip_address')
    list_filter = ('created_at', 'expires_at')
    autocomplete_fields = ('user',)
    list_per_page = 50


@admin.register(CourseContent)
class CourseContentAdmin(ModelAdmin):
    list_display = ('title', 'module', 'order', 'created_at')
    list_filter = ('created_at', 'module__course')
    search_fields = ('title', 'module__title', 'module__course__name')
    autocomplete_fields = ('module',)


class CourseQuizQuestionInline(TabularInline):
    model = CourseQuizQuestion
    extra = 0


@admin.register(CourseQuiz)
class CourseQuizAdmin(ModelAdmin):
    list_display = ('title', 'module', 'pass_score', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at', 'module__course')
    search_fields = ('title', 'module__title')
    autocomplete_fields = ('module',)
    inlines = [CourseQuizQuestionInline]


@admin.register(QuizAttempt)
class QuizAttemptAdmin(ModelAdmin):
    list_display = ('user', 'quiz', 'score', 'submitted_at')
    list_filter = ('submitted_at',)
    search_fields = ('user__username', 'quiz__title')
    autocomplete_fields = ('user', 'quiz')

@admin.register(CourseCertificate)
class CourseCertificateAdmin(ModelAdmin):
    list_display = ('user', 'course', 'certificate_code', 'issued_at')
    list_filter = ('issued_at', 'course')
    search_fields = ('user__username', 'course__name', 'certificate_code')
    autocomplete_fields = ('user', 'course')


@admin.register(CourseChangeRequest)
class CourseChangeRequestAdmin(ModelAdmin):
    list_display = ('course_or_requested_name', 'teacher', 'request_type', 'status', 'created_at', 'reviewed_by', 'reviewed_at')
    list_filter = ('status', 'request_type', 'created_at')
    search_fields = ('course__name', 'requested_course_name', 'teacher__username', 'summary', 'details')
    autocomplete_fields = ('teacher', 'course', 'reviewed_by')
    readonly_fields = ('created_at',)

    def save_model(self, request, obj, form, change):
        if obj.status in ('approved', 'rejected'):
            obj.reviewed_by = request.user
            obj.reviewed_at = timezone.now()
        super().save_model(request, obj, form, change)

    def course_or_requested_name(self, obj):
        if obj.course:
            return obj.course.name
        return obj.requested_course_name or 'N/A'
    course_or_requested_name.short_description = 'Course'


@admin.register(Module)
class ModuleAdmin(ModelAdmin):
    list_display = ('title', 'course')
    search_fields = ('title',)


@admin.register(PaymentInstruction)
class PaymentInstructionAdmin(ModelAdmin):
    list_display = ('id','payment_method_name',  'created_at')
    search_fields = ('payment_method_name',)

# Customize admin site
admin.site.site_header = "Interactive Teaching Platform"
admin.site.site_title = "Teaching Platform Admin"
admin.site.index_title = "Content Management"




