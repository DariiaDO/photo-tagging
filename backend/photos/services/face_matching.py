from __future__ import annotations

from typing import Any

from django.db.models import Max

from photos.models import FaceIdentity


class FaceMatcher:
    def __init__(self, threshold: float = 0.45):
        self.threshold = threshold

    def assign_face_numbers(self, device_id: str, faces: list[dict[str, Any]]) -> list[dict[str, Any]]:
        identities = list(FaceIdentity.objects.filter(device_id=device_id).order_by("number"))

        for face in faces:
            embedding = face.get("embedding")
            if not has_embedding(face):
                continue
            embedding = list(embedding)

            best_identity = None
            best_distance = None
            for identity in identities:
                distance = self.cosine_distance(embedding, identity.embedding or [])
                if best_distance is None or distance < best_distance:
                    best_distance = distance
                    best_identity = identity

            if best_identity is not None and best_distance is not None and best_distance <= self.threshold:
                face["face_number"] = best_identity.number
                continue

            identity = FaceIdentity.objects.create(
                device_id=device_id,
                number=self._next_face_number(device_id),
                embedding=embedding,
            )
            identities.append(identity)
            face["face_number"] = identity.number

        return faces

    @staticmethod
    def cosine_distance(left: list[float], right: list[float]) -> float:
        if not left or not right or len(left) != len(right):
            return 1.0
        similarity = sum(a * b for a, b in zip(left, right))
        return 1.0 - similarity

    @staticmethod
    def _next_face_number(device_id: str) -> int:
        maximum = FaceIdentity.objects.filter(device_id=device_id).aggregate(maximum=Max("number"))["maximum"]
        return int(maximum or 0) + 1


def has_embedding(face: dict[str, Any]) -> bool:
    embedding = face.get("embedding")
    if embedding is None:
        return False
    try:
        return len(embedding) > 0
    except TypeError:
        return bool(embedding)
