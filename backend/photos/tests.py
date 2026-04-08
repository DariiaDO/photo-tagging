from types import SimpleNamespace

from django.test import SimpleTestCase

from .services.face_service import _normalize_bbox, _normalize_face
from .services.vision_api import _extract_description_from_response
from .views import OTHER_ALBUM_NAME, _build_albums, _match_requested_tags


class LlavaResponseParsingTests(SimpleTestCase):
    def test_extract_description_direct_field(self):
        payload = {"description": "A person standing near a car."}
        self.assertEqual(
            _extract_description_from_response(payload),
            "A person standing near a car.",
        )

    def test_extract_description_openai_choices_shape(self):
        payload = {
            "choices": [
                {
                    "message": {
                        "content": "A woman is walking through a busy street."
                    }
                }
            ]
        }
        self.assertEqual(
            _extract_description_from_response(payload),
            "A woman is walking through a busy street.",
        )

    def test_extract_description_nested_data_shape(self):
        payload = {"data": {"answer": "A dog sits on a wooden floor."}}
        self.assertEqual(
            _extract_description_from_response(payload),
            "A dog sits on a wooden floor.",
        )


class FaceServiceNormalizationTests(SimpleTestCase):
    def test_normalize_bbox_adds_size(self):
        self.assertEqual(
            _normalize_bbox([10.2, 20.4, 70.1, 90.6]),
            {
                "x1": 10,
                "y1": 20,
                "x2": 70,
                "y2": 91,
                "width": 60,
                "height": 71,
            },
        )


class AlbumGroupingTests(SimpleTestCase):
    def test_requested_tag_matching_can_return_multiple_albums(self):
        photo = SimpleNamespace(
            category="travel",
            description="A dog sits in a car near the sea.",
            tags=["dog", "sea", "vacation"],
        )

        self.assertEqual(
            _match_requested_tags(photo, ["Dog", "Sea", "Portrait"]),
            ["Dog", "Sea"],
        )

    def test_requested_tag_matching_falls_back_to_other_album(self):
        photo = SimpleNamespace(
            category="portrait",
            description="A smiling person in the studio.",
            tags=["person"],
        )

        self.assertEqual(
            _match_requested_tags(photo, ["Food", "Travel"]),
            [OTHER_ALBUM_NAME],
        )

    def test_requested_tag_matching_supports_default_russian_aliases(self):
        photo = SimpleNamespace(
            category="travel",
            description="A dog sits on the beach during vacation.",
            tags=["dog", "beach"],
        )

        self.assertEqual(
            _match_requested_tags(photo, ["Животные", "Путешествия"]),
            ["Животные", "Путешествия"],
        )

    def test_build_albums_uses_album_names_without_duplication(self):
        albums = _build_albums(
            [
                {
                    "id": 1,
                    "client_photo_id": "uri://1",
                    "album_names": ["Dog", "Travel"],
                },
                {
                    "id": 2,
                    "client_photo_id": "uri://2",
                    "album_names": ["Travel"],
                },
            ]
        )

        self.assertEqual(
            albums,
            [
                {
                    "name": "Dog",
                    "photo_ids": [1],
                    "client_photo_ids": ["uri://1"],
                    "cover_photo_id": 1,
                    "cover_client_photo_id": "uri://1",
                    "photo_count": 1,
                },
                {
                    "name": "Travel",
                    "photo_ids": [1, 2],
                    "client_photo_ids": ["uri://1", "uri://2"],
                    "cover_photo_id": 1,
                    "cover_client_photo_id": "uri://1",
                    "photo_count": 2,
                },
            ],
        )

    def test_normalize_face_returns_bbox_and_score(self):
        face = SimpleNamespace(
            bbox=[12, 18, 44, 66],
            det_score=0.987654321,
            age=27,
            gender=1,
        )
        self.assertEqual(
            _normalize_face(face),
            {
                "bbox": {
                    "x1": 12,
                    "y1": 18,
                    "x2": 44,
                    "y2": 66,
                    "width": 32,
                    "height": 48,
                },
                "det_score": 0.987654,
                "gender": 1,
                "age": 27,
            },
        )
