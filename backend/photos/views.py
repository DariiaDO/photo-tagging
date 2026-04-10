import json
from typing import Any

from django.db.models import Max
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import FaceIdentity, ProcessedImage
from .services.face_service import detect_faces
from .services.vision_api import analyze_image_llava as analyze_image

OTHER_ALBUM_NAME = "Другое"
FACE_ALBUM_PREFIX = "face:"
TAG_ALBUM_PREFIX = "tag:"
FACE_MATCH_THRESHOLD = 0.45
CANONICAL_TAG_ALIASES = {
    "people": {
        "people", "person", "portrait", "face", "man", "woman", "child",
        "люди", "человек", "людей", "мужчина", "женщина", "ребенок", "ребёнок", "лицо", "портрет",
    },
    "nature": {
        "nature", "outdoor", "landscape", "forest", "tree", "sky", "sea", "beach", "mountain",
        "природа", "лес", "дерево", "небо", "море", "пляж", "гора", "пейзаж",
    },
    "animals": {
        "animals", "animal", "dog", "cat", "bird", "horse", "pet",
        "животные", "животное", "собака", "кот", "кошка", "птица", "лошадь", "питомец",
    },
    "food": {
        "food", "meal", "dish", "drink", "fruit", "restaurant", "dessert",
        "еда", "блюдо", "напиток", "фрукт", "ресторан", "десерт",
    },
    "travel": {
        "travel", "trip", "vacation", "tourism", "journey", "landmark", "hotel",
        "путешествия", "путешествие", "поездка", "отпуск", "туризм", "отель", "достопримечательность",
    },
    "transport": {
        "transport", "car", "vehicle", "train", "bus", "bike", "bicycle", "road",
        "транспорт", "машина", "автомобиль", "поезд", "автобус", "велосипед", "дорога",
    },
    "interior": {
        "interior", "room", "office", "kitchen", "bedroom", "table", "chair", "sofa",
        "интерьер", "комната", "офис", "кухня", "спальня", "стол", "стул", "диван",
    },
    "city": {
        "city", "street", "building", "traffic",
        "город", "улица", "здание", "трафик",
    },
    "architecture": {
        "architecture", "facade", "bridge",
        "архитектура", "фасад", "мост",
    },
    "clothing": {
        "clothing", "fashion", "clothes", "dress", "shirt",
        "одежда", "мода", "платье", "рубашка",
    },
    "sports": {
        "sports", "sport", "game", "training", "stadium",
        "спорт", "игра", "тренировка", "стадион",
    },
    "technology": {
        "technology", "device", "computer", "phone", "laptop",
        "технологии", "техника", "устройство", "компьютер", "телефон", "ноутбук",
    },
    "documents": {
        "documents", "document", "text", "page", "table", "paper",
        "документы", "документ", "текст", "страница", "таблица", "бумага",
    },
    "art": {
        "art", "painting", "gallery", "museum", "sculpture",
        "искусство", "картина", "галерея", "музей", "скульптура",
    },
    "night": {
        "night", "dark", "lights",
        "ночь", "темно", "темнота", "огни",
    },
}


def _normalize_text(value: Any) -> str:
    return str(value or "").strip().lower()


ALIAS_TO_CANONICAL = {
    alias: canonical
    for canonical, aliases in CANONICAL_TAG_ALIASES.items()
    for alias in aliases
}


def _album_key(album_type: str, value: str | int) -> str:
    prefix = FACE_ALBUM_PREFIX if album_type == "face" else TAG_ALBUM_PREFIX
    return f"{prefix}{value}"


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


def _get_aliases_for_value(value: Any) -> set[str]:
    normalized = _normalize_text(value)
    if not normalized:
        return set()

    canonical = ALIAS_TO_CANONICAL.get(normalized, normalized)
    aliases = set(CANONICAL_TAG_ALIASES.get(canonical, set()))
    aliases.add(normalized)
    aliases.add(canonical)
    return {alias for alias in aliases if alias}


def _matches_by_alias(haystacks: list[str], aliases: set[str]) -> bool:
    if not aliases:
        return False
    return any(alias in haystack for alias in aliases for haystack in haystacks if haystack)


def _cosine_distance(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 1.0
    similarity = sum(a * b for a, b in zip(left, right))
    return 1.0 - similarity


def _has_embedding(face: dict[str, Any]) -> bool:
    embedding = face.get("embedding")
    if embedding is None:
        return False
    try:
        return len(embedding) > 0
    except TypeError:
        return bool(embedding)


def _next_face_number(device_id: str) -> int:
    maximum = FaceIdentity.objects.filter(device_id=device_id).aggregate(maximum=Max("number"))["maximum"]
    return int(maximum or 0) + 1


def _assign_face_numbers(device_id: str, faces: list[dict[str, Any]]) -> list[dict[str, Any]]:
    identities = list(FaceIdentity.objects.filter(device_id=device_id).order_by("number"))

    for face in faces:
        embedding = face.get("embedding")
        if not _has_embedding(face):
            continue
        embedding = list(embedding)

        best_identity = None
        best_distance = None
        for identity in identities:
            distance = _cosine_distance(embedding, identity.embedding or [])
            if best_distance is None or distance < best_distance:
                best_distance = distance
                best_identity = identity

        if best_identity is not None and best_distance is not None and best_distance <= FACE_MATCH_THRESHOLD:
            face["face_number"] = best_identity.number
            continue

        identity = FaceIdentity.objects.create(
            device_id=device_id,
            number=_next_face_number(device_id),
            embedding=embedding,
        )
        identities.append(identity)
        face["face_number"] = identity.number

    return faces


def _match_requested_tags(photo: ProcessedImage, requested_tags: list[str]) -> list[str]:
    category_haystack = _normalize_text(photo.category)
    tags_haystacks = [_normalize_text(tag) for tag in (photo.tags or [])]
    description_haystack = _normalize_text(photo.description)
    secondary_haystacks = [*tags_haystacks, description_haystack]

    category_matches: list[str] = []
    secondary_matches: list[str] = []

    for requested_tag in requested_tags:
        tag = requested_tag.strip()
        if not tag:
            continue

        aliases = _get_aliases_for_value(tag)
        if category_haystack and _matches_by_alias([category_haystack], aliases):
            if tag not in category_matches:
                category_matches.append(tag)
            continue

        if _matches_by_alias(secondary_haystacks, aliases):
            if tag not in secondary_matches:
                secondary_matches.append(tag)

    matched_tags = category_matches + [tag for tag in secondary_matches if tag not in category_matches]
    return matched_tags or [OTHER_ALBUM_NAME]


def _sanitize_face(face: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in face.items()
        if key != "embedding"
    }


def _ensure_faces_identified(photo: ProcessedImage) -> list[dict[str, Any]]:
    faces = list(photo.faces or [])
    changed = False

    if faces and any(_has_embedding(face) and face.get("face_number") is None for face in faces):
        faces = _assign_face_numbers(photo.device_id, faces)
        changed = True

    if changed:
        photo.faces = faces
        photo.face_count = len(faces)
        photo.save(update_fields=["faces", "face_count"])

    return faces


def _serialize_photo(photo: ProcessedImage, requested_tags: list[str]) -> dict[str, Any]:
    faces = _ensure_faces_identified(photo)
    face_numbers = sorted({int(face["face_number"]) for face in faces if face.get("face_number") is not None})
    tag_names = _match_requested_tags(photo, requested_tags)
    album_keys = [_album_key("tag", tag_name) for tag_name in tag_names]
    album_keys += [_album_key("face", face_number) for face_number in face_numbers]

    return {
        "id": photo.id,
        "client_photo_id": photo.client_photo_id,
        "original_filename": photo.image.name.split("/")[-1] if photo.image else None,
        "image_url": photo.image.url if photo.image else None,
        "tags": photo.tags or [],
        "category": photo.category,
        "description": photo.description,
        "faces": [_sanitize_face(face) for face in faces],
        "face_count": photo.face_count,
        "face_numbers": face_numbers,
        "album_keys": album_keys,
    }


def _build_albums(photo_items: list[dict[str, Any]], requested_tags: list[str]) -> list[dict[str, Any]]:
    albums_by_key: dict[str, dict[str, Any]] = {}

    for requested_tag in requested_tags or [OTHER_ALBUM_NAME]:
        key = _album_key("tag", requested_tag)
        albums_by_key.setdefault(
            key,
            {
                "key": key,
                "name": requested_tag,
                "type": "tag",
                "face_number": None,
                "photo_ids": [],
                "client_photo_ids": [],
                "cover_photo_id": None,
                "cover_client_photo_id": None,
                "photo_count": 0,
            },
        )

    other_key = _album_key("tag", OTHER_ALBUM_NAME)
    albums_by_key.setdefault(
        other_key,
        {
            "key": other_key,
            "name": OTHER_ALBUM_NAME,
            "type": "tag",
            "face_number": None,
            "photo_ids": [],
            "client_photo_ids": [],
            "cover_photo_id": None,
            "cover_client_photo_id": None,
            "photo_count": 0,
        },
    )

    for photo in photo_items:
        for album_key in photo.get("album_keys") or [other_key]:
            if album_key.startswith(FACE_ALBUM_PREFIX):
                face_number = int(album_key.split(":", 1)[1])
                album = albums_by_key.setdefault(
                    album_key,
                    {
                        "key": album_key,
                        "name": f"Лицо #{face_number}",
                        "type": "face",
                        "face_number": face_number,
                        "photo_ids": [],
                        "client_photo_ids": [],
                        "cover_photo_id": None,
                        "cover_client_photo_id": None,
                        "photo_count": 0,
                    },
                )
            else:
                album_name = album_key.split(":", 1)[1]
                album = albums_by_key.setdefault(
                    album_key,
                    {
                        "key": album_key,
                        "name": album_name,
                        "type": "tag",
                        "face_number": None,
                        "photo_ids": [],
                        "client_photo_ids": [],
                        "cover_photo_id": None,
                        "cover_client_photo_id": None,
                        "photo_count": 0,
                    },
                )

            album["photo_ids"].append(photo["id"])
            if photo.get("client_photo_id"):
                album["client_photo_ids"].append(photo["client_photo_id"])
            if album["cover_photo_id"] is None:
                album["cover_photo_id"] = photo["id"]
                album["cover_client_photo_id"] = photo.get("client_photo_id")
            album["photo_count"] += 1

    return sorted(
        albums_by_key.values(),
        key=lambda item: (0 if item["type"] == "tag" else 1, item["name"].lower()),
    )


class ImageUploadView(APIView):
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
                return Response({"detail": "client_photo_id cannot be empty."}, status=400)

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
                faces = _assign_face_numbers(device_id, detect_faces(image_path))
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
                "albums": _build_albums(serialized_photos, requested_tags),
                "stats": {
                    "uploaded_count": uploaded_count,
                    "reused_count": reused_count,
                    "total_count": len(serialized_photos),
                },
            }
        )


class HealthCheckView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        return Response({"status": "ok"})
