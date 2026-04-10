from django.urls import path
from .views import HealthCheckView, ImageUploadView

urlpatterns = [
    path("upload/", ImageUploadView.as_view()),
    path("health/", HealthCheckView.as_view()),
]
