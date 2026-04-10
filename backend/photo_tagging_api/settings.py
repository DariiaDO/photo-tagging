from pathlib import Path
import os


BASE_DIR = Path(__file__).resolve().parent.parent


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _env_list(name: str, default: list[str]) -> list[str]:
    raw = os.getenv(name, "")
    if not raw.strip():
        return default
    return [item.strip() for item in raw.split(",") if item.strip()]


SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "django-insecure-dev-key")
DEBUG = _env_bool("DJANGO_DEBUG", True)
ALLOWED_HOSTS = _env_list(
    "DJANGO_ALLOWED_HOSTS",
    ["127.0.0.1", "localhost"],
)


INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "photos",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "photo_tagging_api.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "photo_tagging_api.wsgi.application"


POSTGRES_DB = os.getenv("POSTGRES_DB", "photo_app")
POSTGRES_USER = os.getenv("POSTGRES_USER", "photo_app")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "photo_app")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = _env_int("POSTGRES_PORT", 5432)
USE_POSTGRES = _env_bool("USE_POSTGRES", False)

if USE_POSTGRES:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": POSTGRES_DB,
            "USER": POSTGRES_USER,
            "PASSWORD": POSTGRES_PASSWORD,
            "HOST": POSTGRES_HOST,
            "PORT": POSTGRES_PORT,
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }


AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


LANGUAGE_CODE = "en-us"
TIME_ZONE = os.getenv("DJANGO_TIME_ZONE", "UTC")
USE_I18N = True
USE_L10N = True
USE_TZ = True

MEDIA_URL = os.getenv("DJANGO_MEDIA_URL", "/media/")
MEDIA_ROOT = Path(os.getenv("DJANGO_MEDIA_ROOT", str(BASE_DIR / "media")))
STATIC_URL = os.getenv("DJANGO_STATIC_URL", "/static/")
STATIC_ROOT = Path(os.getenv("DJANGO_STATIC_ROOT", str(BASE_DIR / "staticfiles")))

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

DATA_UPLOAD_MAX_MEMORY_SIZE = _env_int("DATA_UPLOAD_MAX_MEMORY_SIZE", 10 * 1024 * 1024)
FILE_UPLOAD_MAX_MEMORY_SIZE = _env_int("FILE_UPLOAD_MAX_MEMORY_SIZE", 10 * 1024 * 1024)

LLAVA_ENDPOINT_URL = os.getenv(
    "LLAVA_ENDPOINT_URL",
    os.getenv("LLAVA_COLAB_URL", ""),
).strip()
LLAVA_PROMPT = os.getenv(
    "LLAVA_PROMPT",
    "Describe the image in detail in English in 4 to 5 sentences. "
    "Focus on clearly visible primary subjects, the setting, lighting, and key actions. "
    "Be literal and avoid guessing.",
)
LLAVA_TIMEOUT_SECONDS = _env_int("LLAVA_TIMEOUT_SECONDS", 120)
LLAVA_AUTH_TOKEN = os.getenv("LLAVA_AUTH_TOKEN", "").strip()
TRANSLATE_TO_RUSSIAN = _env_bool("TRANSLATE_TO_RUSSIAN", False)

FACE_DETECTION_ENABLED = _env_bool("FACE_DETECTION_ENABLED", False)
FACE_ANALYSIS_MODEL_NAME = os.getenv("FACE_ANALYSIS_MODEL_NAME", "buffalo_l")
FACE_ANALYSIS_CTX_ID = _env_int("FACE_ANALYSIS_CTX_ID", 0)
FACE_ANALYSIS_DET_SIZE = (
    _env_int("FACE_ANALYSIS_DET_WIDTH", 640),
    _env_int("FACE_ANALYSIS_DET_HEIGHT", 640),
)
FACE_ANALYSIS_PROVIDERS = _env_list("FACE_ANALYSIS_PROVIDERS", ["CPUExecutionProvider"])
FACE_MIN_SIZE_PX = _env_int("FACE_MIN_SIZE_PX", 48)
FACE_MIN_AREA_RATIO = _env_float("FACE_MIN_AREA_RATIO", 0.0025)

LLAVA_PREFERRED_TAGS = [
    "person",
    "food",
    "car",
    "dog",
    "cat",
    "child",
]
