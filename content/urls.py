from django.urls import path
from . import views

app_name = 'content'

urlpatterns = [
    # ── Page views ──────────────────────────────────────────────
    path('', views.home, name='home'),
    path('category/<slug:cat_slug>/', views.category_detail, name='category_detail'),
    path('category/<slug:cat_slug>/<slug:subcat_slug>/', views.subcategory_detail, name='subcategory_detail'),
    path('category/<slug:cat_slug>/<slug:subcat_slug>/<slug:subject_slug>/', views.subject_detail, name='subject_detail'),

    # ── Frontend editor ─────────────────────────────────────────
    path('editor/subject/<int:subject_id>/', views.subject_editor, name='subject_editor'),

    # ── Read API ────────────────────────────────────────────────
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
