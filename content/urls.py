from django.urls import path, include
from django.contrib.auth import views as auth_views
from . import views

app_name = 'content'

urlpatterns = [
    # ── Page views ──────────────────────────────────────────────
    path('', views.home, name='home'),
    path('accounts/login/', views.login_selector, name='login'),
    path('accounts/signup/', views.signup_selector, name='signup'),
    path('accounts/login/student/', views.student_login, name='student_login'),
    path('accounts/login/teacher/', views.teacher_login, name='teacher_login'),
    path('accounts/signup/student/', views.student_signup, name='student_signup'),
    path('accounts/signup/teacher/', views.teacher_signup, name='teacher_signup'),
    path('accounts/logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('profile/', views.profile_page, name='profile'),
    path('dashboard/student/', views.student_dashboard, name='student_dashboard'),
    path('dashboard/teacher/', views.teacher_dashboard, name='teacher_dashboard'),
    path('dashboard/teacher/course/new-request/', views.submit_new_course_request, name='submit_new_course_request'),
    path('dashboard/teacher/course/<int:course_id>/', views.teacher_course_detail, name='teacher_course_detail'),
    path('dashboard/teacher/course/<int:course_id>/change-request/', views.submit_course_change_request, name='submit_course_change_request'),
    path('dashboard/course/<int:course_id>/claim-certificate/', views.claim_certificate, name='claim_certificate'),
    path('subject/<int:subject_id>/complete/', views.mark_subject_complete, name='mark_subject_complete'),
    path('my-courses/', views.my_modules, name='my_courses'),
    path('my-modules/', views.my_modules, name='my_modules'),
    path('category/<slug:cat_slug>/', views.category_detail, name='category_detail'),
    path('category/<slug:cat_slug>/details/<slug:subcat_slug>/', views.subcategory_detail, name='category_details'),
    path('category/<slug:cat_slug>/<slug:subcat_slug>/', views.subcategory_detail, name='subcategory_detail'),
    path('category/<slug:cat_slug>/<slug:subcat_slug>/buy/', views.buy_module, name='buy_module'),
    path('category/<slug:cat_slug>/<slug:subcat_slug>/<slug:subject_slug>/', views.subject_detail, name='subject_detail'),

    # ── Frontend editor ─────────────────────────────────────────
    path('editor/subject/<int:subject_id>/', views.subject_editor, name='subject_editor'),

    # ── Read API ────────────────────────────────────────────────
    path('api/v1/', include('content.api_urls')),

    # ── Legacy AJAX API ─────────────────────────────────────────
    path('api/content/<int:content_id>/', views.get_interactive_content, name='get_interactive_content'),
    path('api/subject/<int:subject_id>/', views.api_subject, name='api_subject'),

    # ── Subject save API ────────────────────────────────────────
    path('api/subject/<int:subject_id>/save/', views.api_subject_save, name='api_subject_save'),

    # ── Interactive content CRUD ─────────────────────────────────
    path('api/subject/<int:subject_id>/ic/create/', views.api_ic_create, name='api_ic_create'),
    path('api/ic/<int:ic_id>/update/', views.api_ic_update, name='api_ic_update'),
    path('api/ic/<int:ic_id>/delete/', views.api_ic_delete, name='api_ic_delete'),

    # ── Accordion section CRUD ───────────────────────────────────
    path('api/subject/<int:subject_id>/accordion/create/', views.api_accordion_create, name='api_accordion_create'),
    path('api/accordion/<int:section_id>/update/', views.api_accordion_update, name='api_accordion_update'),
    path('api/accordion/<int:section_id>/delete/', views.api_accordion_delete, name='api_accordion_delete'),
]
