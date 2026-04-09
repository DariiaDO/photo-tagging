from __future__ import annotations

from math import sqrt
from typing import Any

from django.conf import settings

_FACE_ANALYZER = None
_FACE_ANALYZER_ERROR = None


def _get_face_app():
    global _FACE_ANALYZER, _FACE_ANALYZER_ERROR

    if _FACE_ANALYZER is not None:
        return _FACE_ANALYZER
    if _FACE_ANALYZER_ERROR is not None:
        raise RuntimeError(_FACE_ANALYZER_ERROR)

    try:
        from insightface.app import FaceAnalysis
    except Exception as exc:
        _FACE_ANALYZER_ERROR = (
            "InsightFace is not installed. Install insightface and onnxruntime "
            "to enable face detection."
        )
        raise RuntimeError(_FACE_ANALYZER_ERROR) from exc

    model_name = getattr(settings, "FACE_ANALYSIS_MODEL_NAME", "buffalo_l")
    providers = getattr(settings, "FACE_ANALYSIS_PROVIDERS", ["CPUExecutionProvider"])
    det_size = getattr(settings, "FACE_ANALYSIS_DET_SIZE", (640, 640))
    ctx_id = getattr(settings, "FACE_ANALYSIS_CTX_ID", 0)

    try:
        app = FaceAnalysis(name=model_name, providers=providers)
        app.prepare(ctx_id=ctx_id, det_size=det_size)
    except Exception as exc:
        _FACE_ANALYZER_ERROR = f"InsightFace initialization failed: {exc}"
        raise RuntimeError(_FACE_ANALYZER_ERROR) from exc

    _FACE_ANALYZER = app
    return _FACE_ANALYZER


def _normalize_bbox(bbox: Any) -> dict[str, int]:
    x1, y1, x2, y2 = [int(round(float(value))) for value in bbox[:4]]
    return {
        "x1": x1,
        "y1": y1,
        "x2": x2,
        "y2": y2,
        "width": max(0, x2 - x1),
        "height": max(0, y2 - y1),
    }


def _normalize_embedding(embedding: Any) -> list[float]:
    if embedding is None:
        return []

    try:
        values = [float(value) for value in embedding]
    except TypeError:
        return []

    length = sqrt(sum(value * value for value in values))
    if length <= 0:
        return []

    return [round(value / length, 8) for value in values]


def _normalize_face(face: Any) -> dict[str, Any]:
    data = {
        "bbox": _normalize_bbox(face.bbox),
        "det_score": round(float(getattr(face, "det_score", 0.0)), 6),
    }

    gender = getattr(face, "gender", None)
    age = getattr(face, "age", None)
    if gender is not None:
        data["gender"] = int(gender)
    if age is not None:
        data["age"] = int(age)

    embedding_source = getattr(face, "normed_embedding", None)
    if embedding_source is None:
        embedding_source = getattr(face, "embedding", None)
    embedding = _normalize_embedding(embedding_source)
    if embedding:
        data["embedding"] = embedding

    return data


def detect_faces(image_path: str) -> list[dict[str, Any]]:
    if not getattr(settings, "FACE_DETECTION_ENABLED", False):
        return []

    try:
        import cv2
    except Exception as exc:
        raise RuntimeError("OpenCV is not installed. Install opencv-python.") from exc

    app = _get_face_app()
    image = cv2.imread(image_path)
    if image is None:
        raise RuntimeError("Could not read image for face detection.")

    faces = app.get(image)
    return [_normalize_face(face) for face in faces]
