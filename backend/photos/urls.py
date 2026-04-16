from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .api import AlbumViewSet, FaceViewSet, HealthCheckView, PhotoViewSet

router = DefaultRouter()
router.register("photos", PhotoViewSet, basename="photos")
router.register("albums", AlbumViewSet, basename="albums")
router.register("faces", FaceViewSet, basename="faces")

legacy_upload = PhotoViewSet.as_view({"post": "upload"})

urlpatterns = [
    path("", include(router.urls)),
    path("upload/", legacy_upload, name="legacy-upload"),
    path("health/", HealthCheckView.as_view(), name="health"),
]
