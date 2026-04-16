from rest_framework import serializers

from .models import FaceIdentity, ProcessedImage
from .services.albums import parse_requested_tags, serialize_photo


class DeviceScopedSerializer(serializers.Serializer):
    device_id = serializers.RegexField(
        regex=r"^[A-Za-z0-9._:-]{8,128}$",
        error_messages={
            "invalid": "device_id must be 8-128 characters and contain only letters, digits, '.', '_', ':', or '-'."
        },
    )


class FaceIdentitySerializer(serializers.ModelSerializer):
    class Meta:
        model = FaceIdentity
        fields = (
            "id",
            "device_id",
            "number",
            "created_at",
        )
        read_only_fields = fields


class PhotoSerializer(serializers.ModelSerializer):
    original_filename = serializers.SerializerMethodField()
    image_url = serializers.SerializerMethodField()
    face_numbers = serializers.SerializerMethodField()
    faces = serializers.SerializerMethodField()
    album_keys = serializers.SerializerMethodField()

    class Meta:
        model = ProcessedImage
        fields = (
            "id",
            "client_photo_id",
            "original_filename",
            "image_url",
            "tags",
            "category",
            "description",
            "faces",
            "face_count",
            "face_numbers",
            "album_keys",
            "created_at",
        )
        read_only_fields = fields

    def _serialized(self, obj):
        cache_name = "_photo_api_serialized"
        cached = getattr(obj, cache_name, None)
        if cached is None:
            cached = serialize_photo(obj, self.context.get("requested_tags", []))
            setattr(obj, cache_name, cached)
        return cached

    def get_original_filename(self, obj):
        return self._serialized(obj)["original_filename"]

    def get_image_url(self, obj):
        return self._serialized(obj)["image_url"]

    def get_face_numbers(self, obj):
        return self._serialized(obj)["face_numbers"]

    def get_faces(self, obj):
        return self._serialized(obj)["faces"]

    def get_album_keys(self, obj):
        return self._serialized(obj)["album_keys"]


class AlbumSerializer(serializers.Serializer):
    key = serializers.CharField()
    name = serializers.CharField()
    type = serializers.ChoiceField(choices=("tag", "face"))
    face_number = serializers.IntegerField(allow_null=True)
    photo_ids = serializers.ListField(child=serializers.IntegerField())
    client_photo_ids = serializers.ListField(child=serializers.CharField())
    cover_photo_id = serializers.IntegerField(allow_null=True)
    cover_client_photo_id = serializers.CharField(allow_null=True)
    photo_count = serializers.IntegerField()


class PhotoUploadRequestSerializer(DeviceScopedSerializer):
    tags_json = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        request = self.context["request"]
        images = request.FILES.getlist("images")
        client_photo_ids = request.data.getlist("client_photo_ids")
        if images and len(client_photo_ids) != len(images):
            raise serializers.ValidationError(
                {"client_photo_ids": "Each uploaded image must have a matching client_photo_id."}
            )

        attrs["images"] = images
        attrs["client_photo_ids"] = [str(value).strip() for value in client_photo_ids]
        attrs["requested_tags"] = parse_requested_tags(attrs.get("tags_json"))
        return attrs


ImageUploadSerializer = PhotoUploadRequestSerializer
