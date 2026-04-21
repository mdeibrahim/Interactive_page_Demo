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
    path('accounts/otp-verify/', views.otp_verify, name='otp_verify'),
    path('accounts/otp-resend/', views.otp_resend, name='otp_resend'),
    # Password reset (using Django auth views)
    path('accounts/password-reset/', auth_views.PasswordResetView.as_view(
        template_name='registration/password_reset_form.html',
        email_template_name='registration/password_reset_email.html',
        success_url='/accounts/password-reset/done/'
    ), name='password_reset'),
    path('accounts/password-reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='registration/password_reset_done.html'
    ), name='password_reset_done'),
    path('accounts/password-reset-confirm/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='registration/password_reset_confirm.html',
        success_url='/accounts/password-reset/complete/'
    ), name='password_reset_confirm'),
    path('accounts/password-reset/complete/', auth_views.PasswordResetCompleteView.as_view(
        template_name='registration/password_reset_complete.html'
    ), name='password_reset_complete'),
    path('accounts/signup/student/', views.student_signup, name='student_signup'),
    path('accounts/signup/teacher/', views.teacher_signup, name='teacher_signup'),
    path('accounts/logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('profile/', views.profile_page, name='profile'),
    path('dashboard/student/', views.student_dashboard, name='student_dashboard'),
    path('dashboard/teacher/', views.teacher_dashboard, name='teacher_dashboard'),
    path('dashboard/teacher/course/new-request/', views.submit_new_course_request, name='submit_new_course_request'),
    path('dashboard/teacher/course/new/', views.add_course_request, name='add_course_request'),
    path('dashboard/teacher/course/<int:course_id>/', views.teacher_course_detail, name='teacher_course_detail'),
    path('dashboard/teacher/course/<int:course_id>/change-request/', views.submit_course_change_request, name='submit_course_change_request'),
    path('dashboard/course/<int:course_id>/claim-certificate/', views.claim_certificate, name='claim_certificate'),
    path('my-courses/', views.my_modules, name='my_courses'),
    path('my-modules/', views.my_modules, name='my_modules'),
    # Course-centric routes (category removed)
    path('courses/<slug:course_slug>/', views.course_detail, name='course_detail'),
    path('courses/<slug:course_slug>/details/', views.course_detail, name='course_details'),
    path('courses/<slug:course_slug>/module/<slug:module_slug>/video/<int:video_id>/', views.play_video, name='play_video'),
    path('courses/<slug:course_slug>/buy/', views.buy_module, name='buy_module'),
    path('courses/<slug:course_slug>/start-purchase/', views.start_purchase, name='start_purchase'),
    path('courses/<slug:course_slug>/purchase/', views.course_purchase, name='course_purchase'),

    # ── Read API ────────────────────────────────────────────────
    path('api/v1/', include('content.api_urls')),
]
