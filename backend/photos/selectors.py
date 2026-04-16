from django.db.models import QuerySet

from .models import ProcessedImage
from .services.albums import get_aliases_for_value, normalize_text


def photos_for_device(device_id: str) -> QuerySet[ProcessedImage]:
    return ProcessedImage.objects.filter(device_id=device_id).order_by("created_at", "id")


def filter_photos(queryset: QuerySet[ProcessedImage], params) -> QuerySet[ProcessedImage]:
    category = str(params.get("category", "")).strip()
    if category:
        queryset = queryset.filter(category__iexact=category)

    face_number = str(params.get("face_number", "")).strip()
    if face_number:
        if not face_number.isdigit():
            return queryset.none()
        requested_face_number = int(face_number)
        matching_ids = [
            photo.id
            for photo in queryset
            if requested_face_number in {
                _safe_int(face.get("face_number"))
                for face in (photo.faces or [])
                if face.get("face_number") is not None
            }
        ]
        queryset = queryset.filter(id__in=matching_ids)

    tags = params.getlist("tags") if hasattr(params, "getlist") else []
    if not tags and params.get("tag"):
        tags = [params.get("tag")]
    if tags:
        queryset = _filter_by_tags(queryset, tags)

    return queryset


def _filter_by_tags(queryset: QuerySet[ProcessedImage], tags: list[str]) -> QuerySet[ProcessedImage]:
    matching_ids = []
    for photo in queryset:
        haystacks = [
            normalize_text(photo.category),
            normalize_text(photo.description),
            *[normalize_text(tag) for tag in (photo.tags or [])],
        ]
        if all(any(alias in haystack for alias in get_aliases_for_value(tag) for haystack in haystacks) for tag in tags):
            matching_ids.append(photo.id)
    return queryset.filter(id__in=matching_ids)


def _safe_int(value) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
