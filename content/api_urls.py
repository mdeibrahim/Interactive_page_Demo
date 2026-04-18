from django.urls import path

from . import api_views


urlpatterns = [
    # Auth
    path('auth/register/', api_views.RegisterAPIView.as_view(), name='api_register'),
    path('auth/login/', api_views.LoginAPIView.as_view(), name='api_login'),
    path('auth/refresh/', api_views.RefreshAccessTokenAPIView.as_view(), name='api_refresh'),
    path('auth/logout/', api_views.LogoutAPIView.as_view(), name='api_logout'),
    path('auth/me/', api_views.MeAPIView.as_view(), name='api_me'),

    # Content
    path('categories/', api_views.CategoryListAPIView.as_view(), name='api_categories'),
    path('categories/<slug:cat_slug>/details/', api_views.CategoryDetailsListAPIView.as_view(), name='api_category_details_list'),
    path('categories/<slug:cat_slug>/details/<slug:subcat_slug>/', api_views.DetailRetrieveAPIView.as_view(), name='api_detail_retrieve'),
    path('categories/<slug:cat_slug>/details/<slug:subcat_slug>/buy/', api_views.BuyDetailAPIView.as_view(), name='api_buy_detail'),
    path(
        'categories/<slug:cat_slug>/details/<slug:subcat_slug>/subjects/<slug:subject_slug>/',
        api_views.SubjectRetrieveAPIView.as_view(),
        name='api_subject_retrieve',
    ),
    path('my-courses/', api_views.MyModulesAPIView.as_view(), name='api_my_courses'),
    path('my-modules/', api_views.MyModulesAPIView.as_view(), name='api_my_modules'),

    # Teacher actions
    path('teacher/subjects/<int:subject_id>/', api_views.TeacherSubjectUpdateAPIView.as_view(), name='api_teacher_subject_update'),
]
