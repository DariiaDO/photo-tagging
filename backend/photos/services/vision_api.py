import os
import re
import mimetypes

import requests
from django.conf import settings
try:
    from deep_translator import GoogleTranslator
except Exception:  # pragma: no cover - optional dependency fallback
    GoogleTranslator = None

TAG_KEYWORDS = {
    "people": {
        "person", "people", "man", "woman", "boy", "girl", "child", "face",
        "человек", "люди", "мужчина", "женщина", "ребенок", "лицо",
    },
    "animals": {
        "animal", "dog", "cat", "bird", "puppy", "kitten",
        "животное", "собака", "кот", "кошка", "птица",
    },
    "food": {
        "food", "meal", "dish", "drink", "pizza", "burger", "cake", "fruit", "vegetable",
        "еда", "блюдо", "напиток", "продукт",
    },
    "transport": {
        "car", "vehicle", "train", "bus", "bike", "bicycle", "road",
        "автомобиль", "машина", "поезд", "автобус", "велосипед",
    },
    "nature": {
        "nature", "forest", "mountain", "sky", "river", "lake", "tree", "beach",
        "природа", "лес", "гора", "небо", "река", "озеро", "дерево",
    },
    "interior": {
        "room", "interior", "office", "kitchen", "bedroom", "table", "chair", "sofa",
        "комната", "интерьер", "офис", "кухня", "спальня",
    },
    "city": {"city", "street", "building", "traffic", "город", "улица", "здание"},
    "architecture": {"architecture", "facade", "bridge", "архитектура", "фасад", "мост"},
    "clothing": {"clothing", "fashion", "clothes", "dress", "одежда", "костюм", "платье", "рубашка"},
    "sports": {"sport", "game", "training", "stadium", "спорт", "тренировка", "игра", "стадион"},
    "technology": {"technology", "device", "computer", "phone", "laptop", "техника", "компьютер", "телефон", "ноутбук"},
    "documents": {"document", "text", "page", "table", "paper", "документ", "текст", "страница", "таблица"},
    "art": {"art", "painting", "gallery", "museum", "sculpture", "искусство", "картина", "музей", "скульптура"},
    "travel": {"travel", "trip", "tourism", "vacation", "hotel", "путешествие", "туризм", "отпуск", "отель"},
    "night": {"night", "dark", "lights", "ночь", "темно", "огни"},
}

STOP_WORDS = {
    "the", "and", "for", "with", "this", "that", "from", "into", "are", "is", "a", "an", "to", "of",
    "и", "в", "на", "с", "по", "для", "это", "как", "или", "а", "к", "из", "у", "за",
}


def _get_prompt() -> str:
    prompt = getattr(
        settings,
        "LLAVA_PROMPT",
        "Describe the image in detail in English in 3-5 sentences. "
        "Mention the main subject, setting, lighting, and key actions.",
    )
    return prompt.strip()


def _get_base_tags() -> list[str]:
    default_tags = [
        "people", "animals", "food", "transport", "nature",
        "interior", "city", "architecture", "clothing", "sports",
        "technology", "documents", "art", "travel", "night",
    ]
    raw = getattr(settings, "LLAVA_BASE_TAGS", getattr(settings, "LLAVA_FIXED_TAGS", default_tags))
    if isinstance(raw, str):
        values = [item.strip().lower() for item in raw.split(",")]
        return [item for item in values if item]
    if isinstance(raw, (list, tuple, set)):
        values = [str(item).strip().lower() for item in raw]
        return [item for item in values if item]
    return default_tags


def _build_prompt(base_prompt: str, base_tags: list[str]) -> str:
    tags_line = ", ".join(base_tags)
    return (
        f"{base_prompt}\n\n"
        f"Preferred tag list: [{tags_line}]. "
        "Use these tags whenever they fit. If none apply, add the most relevant custom tags. "
        "Return the description in English."
    )


def _get_endpoint() -> str:
    endpoint = getattr(settings, "LLAVA_COLAB_URL", "").strip()
    if endpoint:
        return endpoint
    return os.getenv("LLAVA_COLAB_URL", "").strip()


def _get_timeout_seconds() -> int:
    value = getattr(settings, "LLAVA_TIMEOUT_SECONDS", 120)
    try:
        timeout = int(value)
    except (TypeError, ValueError):
        timeout = 120
    return max(10, timeout)


def _get_auth_token() -> str:
    token = getattr(settings, "LLAVA_AUTH_TOKEN", "")
    if token:
        return str(token).strip()
    return os.getenv("LLAVA_AUTH_TOKEN", "").strip()


def _translate_to_russian_enabled() -> bool:
    value = getattr(settings, "TRANSLATE_TO_RUSSIAN", False)
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _translate_to_russian(text: str) -> str:
    if not text or not _translate_to_russian_enabled():
        return text
    if GoogleTranslator is None:
        return text
    try:
        translated = GoogleTranslator(source="auto", target="ru").translate(text)
        return translated.strip() if translated else text
    except Exception:
        return text


def _translate_tags_to_russian(tags: list[str]) -> list[str]:
    if not tags:
        return tags
    if not _translate_to_russian_enabled():
        return tags

    translated_tags: list[str] = []
    for tag in tags:
        translated = _translate_to_russian(tag).lower().strip()
        if not translated:
            translated = tag
        if translated not in translated_tags:
            translated_tags.append(translated)
    return translated_tags


def _extract_base_tags(caption: str, base_tags: list[str]) -> list[str]:
    caption_lower = caption.lower()
    result: list[str] = []

    for tag in base_tags:
        keywords = TAG_KEYWORDS.get(tag, {tag})
        if any(keyword in caption_lower for keyword in keywords):
            result.append(tag)

    return result


def _extract_fallback_tags(caption: str, limit: int = 5) -> list[str]:
    words = re.findall(r"[a-zA-Zа-яА-ЯёЁ]+", caption.lower())
    result: list[str] = []
    for word in words:
        if len(word) < 4 or word in STOP_WORDS:
            continue
        if word not in result:
            result.append(word)
        if len(result) >= limit:
            break
    return result


def _compose_tags(caption: str, base_tags: list[str], limit: int = 8) -> list[str]:
    matched = _extract_base_tags(caption, base_tags)
    fallback = _extract_fallback_tags(caption, limit=limit)
    if matched:
        merged = matched + [tag for tag in fallback if tag not in matched]
        return merged[:limit]
    return fallback[:limit]


def _detect_category(tags: list[str]) -> str:
    if not tags:
        return "unknown"
    return tags[0]


def _extract_description_from_response(payload: dict) -> str:
    for key in ("description", "answer", "caption", "text", "output"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()

    data = payload.get("data")
    if isinstance(data, dict):
        return _extract_description_from_response(data)

    choices = payload.get("choices")
    if isinstance(choices, list) and choices:
        first = choices[0]
        if isinstance(first, dict):
            message = first.get("message")
            if isinstance(message, dict):
                content = message.get("content")
                if isinstance(content, str) and content.strip():
                    return content.strip()
            text = first.get("text")
            if isinstance(text, str) and text.strip():
                return text.strip()

    return ""


def analyze_image_llava(image_path: str) -> dict:
    endpoint = _get_endpoint()
    base_tags = _get_base_tags()
    prompt = _build_prompt(_get_prompt(), base_tags)
    timeout = _get_timeout_seconds()

    if not endpoint:
        return {
            "tags": [],
            "category": "unknown",
            "description": "LLaVA endpoint is not configured. Set LLAVA_COLAB_URL in settings.py.",
        }

    headers = {}
    auth_token = _get_auth_token()
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"

    with open(image_path, "rb") as image_file:
        mime_type, _ = mimetypes.guess_type(image_path)
        files = {
            "image": (
                os.path.basename(image_path),
                image_file,
                mime_type or "image/jpeg",
            )
        }
        data = {"prompt": prompt}
        try:
            response = requests.post(
                endpoint,
                files=files,
                data=data,
                headers=headers,
                timeout=timeout,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            detail = ""
            if getattr(exc, "response", None) is not None:
                detail = f" Response: {exc.response.text[:500]}"
            raise RuntimeError(
                f"LLaVA request failed: {exc}."
                f"{detail} Check LLAVA_COLAB_URL, endpoint availability, and timeout."
            ) from exc

    try:
        payload = response.json()
    except ValueError as exc:
        raise RuntimeError(
            "LLaVA endpoint returned non-JSON response. "
            "Expected a JSON object with 'description' or similar fields."
        ) from exc

    if not isinstance(payload, dict):
        raise RuntimeError(
            "LLaVA endpoint returned unexpected JSON shape. "
            "Expected top-level JSON object."
        )

    caption = _extract_description_from_response(payload)
    if not caption:
        caption = str(payload).strip()

    tags = _compose_tags(caption, base_tags)
    tags = _translate_tags_to_russian(tags)
    category = _detect_category(tags)

    return {
        "tags": tags,
        "category": category,
        "description": _translate_to_russian(caption),
    }


# Backward-compatible aliases for old imports/calls.
analyze_image_blip = analyze_image_llava
analyze_image_gemini = analyze_image_llava
