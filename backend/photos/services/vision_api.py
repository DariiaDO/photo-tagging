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

NON_PROMINENT_PEOPLE_PATTERNS = [
    r"\\bhands?\\b",
    r"\\bhand\\b",
    r"\\barm\\b",
    r"\\bcrowd\\b",
    r"\\bbackground\\b",
    r"\\bdistant\\b",
    r"\\bfar away\\b",
    r"\\bsmall figure\\b",
    r"\\bhands? only\\b",
    r"\\bрук[аи]?\\b",
    r"\\bкист[ьи]\\b",
    r"\\bна заднем плане\\b",
    r"\\bвдали\\b",
    r"\\bтолпа\\b",
]

NON_REAL_ANIMAL_PATTERNS = [
    r"\btoy animal\b",
    r"\bstuffed animal\b",
    r"\bplush animal\b",
    r"\btoy dog\b",
    r"\btoy cat\b",
    r"\bplush dog\b",
    r"\bplush cat\b",
    r"\bteddy\b",
    r"\bdoll\b",
    r"\bfigurine\b",
    r"\bstatue\b",
    r"\billustration of a dog\b",
    r"\billustration of a cat\b",
    r"\bcartoon dog\b",
    r"\bcartoon cat\b",
    r"\bигрушечн\w+\b",
    r"\bплюшев\w+\b",
    r"\bмягк\w+ игрушк\w+\b",
    r"\bкукл\w+\b",
    r"\bстатуэтк\w+\b",
]

REAL_ANIMAL_PATTERNS = [
    r"\blive animal\b",
    r"\breal animal\b",
    r"\breal dog\b",
    r"\breal cat\b",
    r"\bdog\b",
    r"\bcat\b",
    r"\bbird\b",
    r"\bhorse\b",
    r"\bpuppy\b",
    r"\bkitten\b",
    r"\bpet\b",
    r"\bживотн\w+\b",
    r"\bсобак\w+\b",
    r"\bкошк\w+\b",
    r"\bкот\w*\b",
    r"\bптиц\w+\b",
    r"\bлошад\w+\b",
]

PROMINENT_PEOPLE_PATTERNS = [
    r"\\bportrait\\b",
    r"\\bclose[- ]?up\\b",
    r"\\bselfie\\b",
    r"\\bperson\\b",
    r"\\bman\\b",
    r"\\bwoman\\b",
    r"\\bchild\\b",
    r"\\bface\\b",
    r"\\bupper body\\b",
    r"\\bfull body\\b",
    r"\\bstanding\\b",
    r"\\bposing\\b",
    r"\\bпортрет\\b",
    r"\\bкрупным планом\\b",
    r"\\bселфи\\b",
    r"\\bчеловек\\b",
    r"\\bмужчина\\b",
    r"\\bженщина\\b",
    r"\\bребенок\\b",
    r"\\bлицо\\b",
]


def _get_prompt() -> str:
    prompt = getattr(
        settings,
        "LLAVA_PROMPT",
        "Describe the image in detail in English in 3-5 sentences. "
        "Focus on clearly visible primary subjects, the setting, lighting, and key actions. "
        "Be literal and avoid guessing.",
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
        "Only use the people tag when a real person is a main, clearly visible subject occupying a meaningful part of the frame. "
        "Do not use the people tag for only a hand, arm, leg, silhouette, reflection, mannequin, statue, poster, drawing, or any isolated body part. "
        "If people are tiny, distant, heavily blurred, or only in the background, do not use the people tag. "
        "Only use the animals tag for a real living animal that is clearly visible. "
        "Do not tag animals for toys, plushies, figurines, statues, drawings, cartoons, costumes, or animal-shaped objects. "
        "If unsure whether it is a real animal or a toy/object, prefer not to use the animals tag. "
        "Prioritize the dominant foreground subject over small background details. "
        "Return the description in English."
    )


def _get_endpoint() -> str:
    endpoint = getattr(settings, "LLAVA_ENDPOINT_URL", "").strip()
    if endpoint:
        return endpoint
    legacy_endpoint = getattr(settings, "LLAVA_COLAB_URL", "").strip()
    if legacy_endpoint:
        return legacy_endpoint
    return os.getenv("LLAVA_ENDPOINT_URL", os.getenv("LLAVA_COLAB_URL", "")).strip()


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


def _should_keep_people_tag(caption: str) -> bool:
    caption_lower = caption.lower()
    if any(re.search(pattern, caption_lower) for pattern in NON_PROMINENT_PEOPLE_PATTERNS):
        return False
    return any(re.search(pattern, caption_lower) for pattern in PROMINENT_PEOPLE_PATTERNS)


def _should_keep_animals_tag(caption: str) -> bool:
    caption_lower = caption.lower()
    if any(re.search(pattern, caption_lower) for pattern in NON_REAL_ANIMAL_PATTERNS):
        return False
    return any(re.search(pattern, caption_lower) for pattern in REAL_ANIMAL_PATTERNS)


def _extract_base_tags(caption: str, base_tags: list[str]) -> list[str]:
    caption_lower = caption.lower()
    result: list[str] = []

    for tag in base_tags:
        if tag == "people" and not _should_keep_people_tag(caption):
            continue
        if tag == "animals" and not _should_keep_animals_tag(caption):
            continue
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
    fallback = [tag for tag in _extract_fallback_tags(caption, limit=limit) if tag != "people"]
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
            "description": "LLaVA endpoint is not configured. Set LLAVA_ENDPOINT_URL in the environment.",
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
                f"{detail} Check LLAVA_ENDPOINT_URL, service availability, and timeout."
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


analyze_image_blip = analyze_image_llava
analyze_image_gemini = analyze_image_llava
