from rest_framework import serializers

from .models import ProcessedImage


class ImageUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProcessedImage
        fields = (
            "id",
            "device_id",
            "client_photo_id",
            "image",
            "tags",
            "category",
            "description",
            "faces",
            "face_count",
            "created_at",
        )
        read_only_fields = (
            "id",
            "tags",
            "category",
            "description",
            "faces",
            "face_count",
            "created_at",
        )
