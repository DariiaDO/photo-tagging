import logging

from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import FaceIdentity, ProcessedImage
from .responses import error_response
from .selectors import filter_photos, photos_for_device
from .serializers import (
    AlbumSerializer,
    DeviceScopedSerializer,
    FaceIdentitySerializer,
    PhotoSerializer,
    PhotoUploadRequestSerializer,
)
from .services.albums import build_albums, serialize_photo
from .services.face_matching import FaceMatcher
from .services.face_service import detect_faces
from .services.vision_api import analyze_image_llava as analyze_image

logger = logging.getLogger(__name__)


class PhotoViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = PhotoSerializer

    def get_queryset(self):
        device_id = self._validated_device_id()
        queryset = photos_for_device(device_id)
        return filter_photos(queryset, self.request.query_params)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["requested_tags"] = self.request.query_params.getlist("tags")
        return context

    @action(detail=False, methods=["post"], url_path="upload")
    def upload(self, request):
        serializer = PhotoUploadRequestSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        device_id = data["device_id"]
        requested_tags = data["requested_tags"]
        images = data["images"]
        client_photo_ids = data["client_photo_ids"]
        matcher = FaceMatcher()

        uploaded_count = 0
        reused_count = 0

        for index, image_file in enumerate(images):
            client_photo_id = client_photo_ids[index]
            if not client_photo_id:
                return Response(
                    error_response("client_photo_id cannot be empty.", {"index": index}),
                    status=status.HTTP_400_BAD_REQUEST,
                )

            processed_image = ProcessedImage.objects.filter(
                device_id=device_id,
                client_photo_id=client_photo_id,
            ).first()
            if processed_image:
                reused_count += 1
                continue

            processed_image = ProcessedImage.objects.create(
                device_id=device_id,
                client_photo_id=client_photo_id,
                image=image_file,
                category="unknown",
            )
            image_path = processed_image.image.path

            try:
                result = analyze_image(image_path, preferred_tags=requested_tags)
            except Exception as exc:
                logger.exception("LLaVA analysis failed for photo %s", processed_image.id)
                result = {
                    "tags": [],
                    "category": "unknown",
                    "description": f"LLaVA error: {exc}",
                }

            try:
                faces = matcher.assign_face_numbers(device_id, detect_faces(image_path))
            except Exception as exc:
                logger.exception("Face detection failed for photo %s", processed_image.id)
                faces = []
                description = result.get("description", "")
                result["description"] = f"{description} Face detection error: {exc}".strip()

            processed_image.tags = result.get("tags", [])
            processed_image.category = result.get("category", "unknown")
            processed_image.description = result.get("description", "")
            processed_image.faces = faces
            processed_image.face_count = len(faces)
            processed_image.save()
            uploaded_count += 1

        device_photos = photos_for_device(device_id)
        serialized_photos = [serialize_photo(photo, requested_tags) for photo in device_photos]
        albums = build_albums(serialized_photos, requested_tags)

        return Response(
            {
                "requested_tags": requested_tags,
                "photos": PhotoSerializer(
                    device_photos,
                    many=True,
                    context={"requested_tags": requested_tags, "request": request},
                ).data,
                "albums": AlbumSerializer(albums, many=True).data,
                "stats": {
                    "uploaded_count": uploaded_count,
                    "reused_count": reused_count,
                    "total_count": len(serialized_photos),
                },
            }
        )

    def _validated_device_id(self) -> str:
        serializer = DeviceScopedSerializer(data=self.request.query_params)
        serializer.is_valid(raise_exception=True)
        return serializer.validated_data["device_id"]


class AlbumViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = AlbumSerializer
    pagination_class = None

    def list(self, request, *args, **kwargs):
        serializer = DeviceScopedSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        device_id = serializer.validated_data["device_id"]
        requested_tags = request.query_params.getlist("tags")
        photos = [serialize_photo(photo, requested_tags) for photo in photos_for_device(device_id)]
        albums = build_albums(photos, requested_tags)
        return Response(self.get_serializer(albums, many=True).data)


class FaceViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = FaceIdentitySerializer
    pagination_class = None

    def get_queryset(self):
        serializer = DeviceScopedSerializer(data=self.request.query_params)
        serializer.is_valid(raise_exception=True)
        return FaceIdentity.objects.filter(device_id=serializer.validated_data["device_id"]).order_by("number")


class ImageUploadView(APIView):
    def post(self, request):
        return PhotoViewSet.as_view({"post": "upload"})(request._request)


class HealthCheckView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        return Response({"status": "ok"})
