import json
from typing import Any

from photos.models import ProcessedImage
from photos.services.face_matching import FaceMatcher, has_embedding

OTHER_ALBUM_NAME = "Другое"
FACE_ALBUM_PREFIX = "face:"
TAG_ALBUM_PREFIX = "tag:"

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
    "city": {"city", "street", "building", "traffic", "город", "улица", "здание", "трафик"},
    "architecture": {"architecture", "facade", "bridge", "архитектура", "фасад", "мост"},
    "clothing": {"clothing", "fashion", "clothes", "dress", "shirt", "одежда", "мода", "платье", "рубашка"},
    "sports": {"sports", "sport", "game", "training", "stadium", "спорт", "игра", "тренировка", "стадион"},
    "technology": {"technology", "device", "computer", "phone", "laptop", "технологии", "техника", "устройство", "компьютер", "телефон", "ноутбук"},
    "documents": {"documents", "document", "text", "page", "table", "paper", "документы", "документ", "текст", "страница", "таблица", "бумага"},
    "art": {"art", "painting", "gallery", "museum", "sculpture", "искусство", "картина", "галерея", "музей", "скульптура"},
    "night": {"night", "dark", "lights", "ночь", "темно", "темнота", "огни"},
}

ALIAS_TO_CANONICAL = {
    alias: canonical
    for canonical, aliases in CANONICAL_TAG_ALIASES.items()
    for alias in aliases
}


def normalize_text(value: Any) -> str:
    return str(value or "").strip().lower()


def album_key(album_type: str, value: str | int) -> str:
    prefix = FACE_ALBUM_PREFIX if album_type == "face" else TAG_ALBUM_PREFIX
    return f"{prefix}{value}"


def parse_requested_tags(raw_value: Any) -> list[str]:
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


def get_aliases_for_value(value: Any) -> set[str]:
    normalized = normalize_text(value)
    if not normalized:
        return set()

    canonical = ALIAS_TO_CANONICAL.get(normalized, normalized)
    aliases = set(CANONICAL_TAG_ALIASES.get(canonical, set()))
    aliases.add(normalized)
    aliases.add(canonical)
    return {alias for alias in aliases if alias}


def matches_by_alias(haystacks: list[str], aliases: set[str]) -> bool:
    if not aliases:
        return False
    return any(alias in haystack for alias in aliases for haystack in haystacks if haystack)


def match_requested_tags(photo: ProcessedImage, requested_tags: list[str]) -> list[str]:
    category_haystack = normalize_text(photo.category)
    tags_haystacks = [normalize_text(tag) for tag in (photo.tags or [])]
    description_haystack = normalize_text(photo.description)
    secondary_haystacks = [*tags_haystacks, description_haystack]

    category_matches: list[str] = []
    secondary_matches: list[str] = []

    for requested_tag in requested_tags:
        tag = requested_tag.strip()
        if not tag:
            continue

        aliases = get_aliases_for_value(tag)
        if category_haystack and matches_by_alias([category_haystack], aliases):
            if tag not in category_matches:
                category_matches.append(tag)
            continue

        if matches_by_alias(secondary_haystacks, aliases) and tag not in secondary_matches:
            secondary_matches.append(tag)

    matched_tags = category_matches + [tag for tag in secondary_matches if tag not in category_matches]
    return matched_tags or [OTHER_ALBUM_NAME]


def sanitize_face(face: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in face.items() if key != "embedding"}


def ensure_faces_identified(photo: ProcessedImage, matcher: FaceMatcher | None = None) -> list[dict[str, Any]]:
    faces = list(photo.faces or [])
    changed = False

    if faces and any(has_embedding(face) and face.get("face_number") is None for face in faces):
        faces = (matcher or FaceMatcher()).assign_face_numbers(photo.device_id, faces)
        changed = True

    if changed:
        photo.faces = faces
        photo.face_count = len(faces)
        photo.save(update_fields=["faces", "face_count"])

    return faces


def serialize_photo(photo: ProcessedImage, requested_tags: list[str]) -> dict[str, Any]:
    faces = ensure_faces_identified(photo)
    face_numbers = sorted({int(face["face_number"]) for face in faces if face.get("face_number") is not None})
    tag_names = match_requested_tags(photo, requested_tags)
    album_keys = [album_key("tag", tag_name) for tag_name in tag_names]
    album_keys += [album_key("face", face_number) for face_number in face_numbers]

    return {
        "id": photo.id,
        "client_photo_id": photo.client_photo_id,
        "original_filename": photo.image.name.split("/")[-1] if photo.image else None,
        "image_url": photo.image.url if photo.image else None,
        "tags": tag_names,
        "category": photo.category,
        "description": photo.description,
        "faces": [sanitize_face(face) for face in faces],
        "face_count": photo.face_count,
        "face_numbers": face_numbers,
        "album_keys": album_keys,
        "created_at": photo.created_at,
    }


def build_albums(photo_items: list[dict[str, Any]], requested_tags: list[str]) -> list[dict[str, Any]]:
    albums_by_key: dict[str, dict[str, Any]] = {}

    for requested_tag in requested_tags or [OTHER_ALBUM_NAME]:
        key = album_key("tag", requested_tag)
        albums_by_key.setdefault(key, empty_album(key, requested_tag, "tag"))

    other_key = album_key("tag", OTHER_ALBUM_NAME)
    albums_by_key.setdefault(other_key, empty_album(other_key, OTHER_ALBUM_NAME, "tag"))

    for photo in photo_items:
        for key in photo.get("album_keys") or [other_key]:
            if key.startswith(FACE_ALBUM_PREFIX):
                face_number = int(key.split(":", 1)[1])
                album = albums_by_key.setdefault(
                    key,
                    empty_album(key, f"Лицо #{face_number}", "face", face_number),
                )
            else:
                album_name = key.split(":", 1)[1]
                album = albums_by_key.setdefault(key, empty_album(key, album_name, "tag"))

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


def empty_album(key: str, name: str, album_type: str, face_number: int | None = None) -> dict[str, Any]:
    return {
        "key": key,
        "name": name,
        "type": album_type,
        "face_number": face_number,
        "photo_ids": [],
        "client_photo_ids": [],
        "cover_photo_id": None,
        "cover_client_photo_id": None,
        "photo_count": 0,
    }
