from django.urls import path

from . import views

app_name = "operations"
urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("sources/<int:source_id>/<str:action>/", views.source_action, name="source_action"),
    path("reviews/", views.reviews, name="reviews"),
    path("reviews/<int:review_id>/<str:action>/", views.review_action, name="review_action"),
    path("settings/", views.settings_view, name="settings"),
    path("templates/preview/", views.template_preview, name="template_preview"),
    path("templates/<int:template_id>/activate/", views.template_activate, name="template_activate"),
    path("admins/<int:user_id>/reset-password/", views.password_reset, name="password_reset"),
    path("queue/<int:queue_id>/retry/", views.queue_retry, name="queue_retry"),
    path("media/<int:candidate_id>/retry/", views.media_retry, name="media_retry"),
    path("publications/<int:publication_id>/retry/", views.publication_retry, name="publication_retry"),
]
