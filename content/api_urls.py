from django.urls import path

from . import api_views


urlpatterns = [
    # Auth
    path('auth/register/', api_views.RegisterAPIView.as_view(), name='api_register'),
    path('auth/login/', api_views.LoginAPIView.as_view(), name='api_login'),
    path('auth/refresh/', api_views.RefreshAccessTokenAPIView.as_view(), name='api_refresh'),
    path('auth/logout/', api_views.LogoutAPIView.as_view(), name='api_logout'),
    path('auth/me/', api_views.MeAPIView.as_view(), name='api_me'),

    # Content (course-centric)
    path('courses/<slug:course_slug>/', api_views.DetailRetrieveAPIView.as_view(), name='api_detail_retrieve'),
    path('courses/<slug:course_slug>/buy/', api_views.BuyDetailAPIView.as_view(), name='api_buy_detail'),
    path('my-courses/', api_views.MyModulesAPIView.as_view(), name='api_my_courses'),
    path('my-modules/', api_views.MyModulesAPIView.as_view(), name='api_my_modules'),
]
