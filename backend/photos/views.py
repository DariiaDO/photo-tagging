import json
from typing import Any

from rest_framework.response import Response
from rest_framework.views import APIView

from .models import ProcessedImage
from .services.face_service import detect_faces
from .services.vision_api import analyze_image_llava as analyze_image

OTHER_ALBUM_NAME = "Другое"
TAG_ALIASES = {
    "люди": ["люди", "человек", "людей", "person", "people", "portrait", "face", "man", "woman", "child"],
    "природа": ["природа", "nature", "outdoor", "landscape", "forest", "tree", "sky", "sea", "beach", "mountain"],
    "животные": ["животные", "animal", "animals", "dog", "cat", "bird", "horse", "pet"],
    "еда": ["еда", "food", "meal", "dish", "drink", "fruit", "restaurant", "dessert"],
    "путешествия": ["путешествия", "travel", "trip", "vacation", "tourism", "journey", "landmark", "hotel"],
}


def _normalize_text(value: Any) -> str:
    return str(value or "").strip().lower()


def _parse_requested_tags(raw_value: Any) -> list[str]:
    if raw_value is None:
        return []

    if isinstance(raw_value, list):
        raw_tags = raw_value
    else:
        text = str(raw_value).strip()
        if not text:
            return []
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            parsed = [part.strip() for part in text.split(",")]
        raw_tags = parsed if isinstance(parsed, list) else []

    normalized_tags = []
    for raw_tag in raw_tags:
        tag = str(raw_tag).strip()
        if tag and tag not in normalized_tags:
            normalized_tags.append(tag)
    return normalized_tags


def _match_requested_tags(photo: ProcessedImage, requested_tags: list[str]) -> list[str]:
    haystacks = [
        _normalize_text(photo.category),
        _normalize_text(photo.description),
        *[_normalize_text(tag) for tag in (photo.tags or [])],
    ]

    matched_tags = []
    for requested_tag in requested_tags:
        tag = requested_tag.strip()
        normalized_tag = tag.lower()
        if not normalized_tag:
            continue

        aliases = TAG_ALIASES.get(normalized_tag, [normalized_tag])
        if any(alias in haystack for alias in aliases for haystack in haystacks if haystack):
            matched_tags.append(tag)

    return matched_tags or [OTHER_ALBUM_NAME]


def _serialize_photo(photo: ProcessedImage, requested_tags: list[str]) -> dict[str, Any]:
    album_names = _match_requested_tags(photo, requested_tags)
    return {
        "id": photo.id,
        "client_photo_id": photo.client_photo_id,
        "original_filename": photo.image.name.split("/")[-1] if photo.image else None,
        "image_url": photo.image.url if photo.image else None,
        "tags": photo.tags or [],
        "category": photo.category,
        "description": photo.description,
        "faces": photo.faces or [],
        "face_count": photo.face_count,
        "album_names": album_names,
    }


def _build_albums(photo_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    albums_by_name: dict[str, dict[str, Any]] = {}

    for photo in photo_items:
        for album_name in photo.get("album_names") or [OTHER_ALBUM_NAME]:
            album = albums_by_name.setdefault(
                album_name,
                {
                    "name": album_name,
                    "photo_ids": [],
                    "client_photo_ids": [],
                    "cover_photo_id": photo["id"],
                    "cover_client_photo_id": photo.get("client_photo_id"),
                    "photo_count": 0,
                },
            )
            album["photo_ids"].append(photo["id"])
            if photo.get("client_photo_id"):
                album["client_photo_ids"].append(photo["client_photo_id"])
            album["photo_count"] += 1

    return sorted(albums_by_name.values(), key=lambda item: item["name"].lower())


class ImageUploadView(APIView):
    """
    Syncs client photos with the backend and returns the full device snapshot
    grouped into albums defined by the requested tags.
    """

    def post(self, request):
        device_id = str(request.data.get("device_id", "")).strip()
        if not device_id:
            return Response({"detail": "Field 'device_id' is required."}, status=400)

        requested_tags = _parse_requested_tags(request.data.get("tags_json"))
        images = request.FILES.getlist("images")
        client_photo_ids = [str(value).strip() for value in request.data.getlist("client_photo_ids")]

        if images and len(client_photo_ids) != len(images):
            return Response(
                {"detail": "Each uploaded image must have a matching client_photo_id."},
                status=400,
            )

        uploaded_count = 0
        reused_count = 0

        for index, image_file in enumerate(images):
            client_photo_id = client_photo_ids[index]
            if not client_photo_id:
                return Response(
                    {"detail": "client_photo_id cannot be empty."},
                    status=400,
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
                result = analyze_image(image_path)
            except Exception as exc:
                result = {
                    "tags": [],
                    "category": "unknown",
                    "description": f"LLaVA error: {exc}",
                }

            try:
                faces = detect_faces(image_path)
            except Exception as exc:
                faces = []
                description = result.get("description", "")
                detail = f" Face detection error: {exc}"
                result["description"] = f"{description}{detail}".strip()

            processed_image.tags = result.get("tags", [])
            processed_image.category = result.get("category", "unknown")
            processed_image.description = result.get("description", "")
            processed_image.faces = faces
            processed_image.face_count = len(faces)
            processed_image.save()
            uploaded_count += 1

        device_photos = ProcessedImage.objects.filter(device_id=device_id).order_by("created_at")
        serialized_photos = [_serialize_photo(photo, requested_tags) for photo in device_photos]

        return Response(
            {
                "requested_tags": requested_tags,
                "photos": serialized_photos,
                "albums": _build_albums(serialized_photos),
                "stats": {
                    "uploaded_count": uploaded_count,
                    "reused_count": reused_count,
                    "total_count": len(serialized_photos),
                },
            }
        )

