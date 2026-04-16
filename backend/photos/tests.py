from types import SimpleNamespace

from pathlib import Path
from unittest.mock import patch

import numpy as np
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase
from django.test.utils import override_settings
from rest_framework.test import APIClient

from .models import ProcessedImage
from .services.face_service import (
    _normalize_bbox,
    _normalize_embedding,
    _normalize_face,
    _should_keep_face,
)
from .services.vision_api import (
    _extract_base_tags,
    _extract_description_from_response,
    _get_base_tags,
    _should_keep_animals_tag,
    _should_keep_people_tag,
)
from .views import OTHER_ALBUM_NAME, _build_albums, _has_embedding, _match_requested_tags


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

    def test_normalize_embedding_returns_unit_vector(self):
        self.assertEqual(
            _normalize_embedding([3.0, 4.0]),
            [0.6, 0.8],
        )

    def test_normalize_face_returns_bbox_score_and_embedding(self):
        face = SimpleNamespace(
            bbox=[12, 18, 44, 66],
            det_score=0.987654321,
            age=27,
            gender=1,
            normed_embedding=[0.5, 0.5],
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
                "embedding": [0.70710678, 0.70710678],
            },
        )

    def test_normalize_face_supports_numpy_normed_embedding(self):
        face = SimpleNamespace(
            bbox=[12, 18, 44, 66],
            det_score=0.9,
            normed_embedding=np.array([0.5, 0.5]),
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
                "det_score": 0.9,
                "embedding": [0.70710678, 0.70710678],
            },
        )

    @override_settings(FACE_MIN_SIZE_PX=48, FACE_MIN_AREA_RATIO=0.0025)
    def test_should_keep_face_rejects_tiny_background_face(self):
        self.assertFalse(
            _should_keep_face(
                {"width": 30, "height": 36},
                image_width=1600,
                image_height=1200,
            )
        )

    @override_settings(FACE_MIN_SIZE_PX=48, FACE_MIN_AREA_RATIO=0.0025)
    def test_should_keep_face_accepts_large_face(self):
        self.assertTrue(
            _should_keep_face(
                {"width": 140, "height": 160},
                image_width=1600,
                image_height=1200,
            )
        )


class VisionPromptHeuristicsTests(SimpleTestCase):
    def test_people_tag_is_removed_for_body_part_only(self):
        self.assertFalse(_should_keep_people_tag("A close-up of a hand holding a cup."))

    def test_animals_tag_is_removed_for_toy(self):
        self.assertFalse(_should_keep_animals_tag("A plush dog toy on a shelf."))

    def test_animals_tag_is_kept_for_real_animal(self):
        self.assertTrue(_should_keep_animals_tag("A dog is running across the grass."))

    def test_extract_base_tags_skips_people_for_hand_only_caption(self):
        tags = _extract_base_tags(
            "A hand holding a phone near a window.",
            _get_base_tags(),
        )
        self.assertNotIn("people", tags)

    def test_extract_base_tags_skips_animals_for_plush_toy_caption(self):
        tags = _extract_base_tags(
            "A plush dog toy sitting on a bed.",
            _get_base_tags(),
        )
        self.assertNotIn("animals", tags)


class FaceEmbeddingHelpersTests(SimpleTestCase):
    def test_has_embedding_supports_numpy_arrays(self):
        self.assertTrue(_has_embedding({"embedding": np.array([0.1, 0.2, 0.3])}))
        self.assertFalse(_has_embedding({"embedding": np.array([])}))


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

    def test_requested_tag_matching_prioritizes_category_before_other_tags(self):
        photo = SimpleNamespace(
            category="travel",
            description="A dog sits in a car near the sea.",
            tags=["dog", "sea", "vacation"],
        )

        self.assertEqual(
            _match_requested_tags(photo, ["Животные", "Путешествия"]),
            ["Путешествия", "Животные"],
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
            ["Путешествия", "Животные"],
        )

    def test_requested_tag_matching_supports_english_requested_tag_for_russian_category(self):
        photo = SimpleNamespace(
            category="животные",
            description="Собака сидит на траве.",
            tags=["собака"],
        )

        self.assertEqual(
            _match_requested_tags(photo, ["Animals", "Travel"]),
            ["Animals"],
        )

    def test_requested_tag_matching_supports_russian_requested_tag_for_english_category(self):
        photo = SimpleNamespace(
            category="transport",
            description="A train arrives at the station.",
            tags=["train", "station"],
        )

        self.assertEqual(
            _match_requested_tags(photo, ["Транспорт", "Путешествия"]),
            ["Транспорт"],
        )

    def test_build_albums_includes_face_albums(self):
        albums = _build_albums(
            [
                {
                    "id": 1,
                    "client_photo_id": "uri://1",
                    "album_keys": ["tag:Животные", "face:2"],
                },
                {
                    "id": 2,
                    "client_photo_id": "uri://2",
                    "album_keys": ["face:2"],
                },
            ],
            ["Животные"],
        )

        self.assertEqual(
            albums,
            [
                {
                    "key": "tag:Другое",
                    "name": "Другое",
                    "type": "tag",
                    "face_number": None,
                    "photo_ids": [],
                    "client_photo_ids": [],
                    "cover_photo_id": None,
                    "cover_client_photo_id": None,
                    "photo_count": 0,
                },
                {
                    "key": "tag:Животные",
                    "name": "Животные",
                    "type": "tag",
                    "face_number": None,
                    "photo_ids": [1],
                    "client_photo_ids": ["uri://1"],
                    "cover_photo_id": 1,
                    "cover_client_photo_id": "uri://1",
                    "photo_count": 1,
                },
                {
                    "key": "face:2",
                    "name": "Лицо #2",
                    "type": "face",
                    "face_number": 2,
                    "photo_ids": [1, 2],
                    "client_photo_ids": ["uri://1", "uri://2"],
                    "cover_photo_id": 1,
                    "cover_client_photo_id": "uri://1",
                    "photo_count": 2,
                },
            ],
        )


class PhotoApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.media_root = Path(__file__).resolve().parent / "test_media"
        self.override = override_settings(
            MEDIA_ROOT=self.media_root,
            FACE_DETECTION_ENABLED=True,
        )
        self.override.enable()

    def tearDown(self):
        self.override.disable()
        for image_file in (self.media_root / "images").glob("*"):
            if image_file.name != ".gitkeep":
                image_file.unlink(missing_ok=True)

    @patch("photos.api.detect_faces")
    @patch("photos.api.analyze_image")
    def test_upload_endpoint_processes_photo_and_returns_snapshot(self, analyze_image, detect_faces):
        analyze_image.return_value = {
            "tags": ["animals", "dog"],
            "category": "animals",
            "description": "A dog in a park.",
        }
        detect_faces.return_value = [
            {
                "bbox": {"x1": 0, "y1": 0, "x2": 80, "y2": 80, "width": 80, "height": 80},
                "embedding": [1.0, 0.0],
            }
        ]

        response = self.client.post(
            "/api/photos/upload/",
            data={
                "device_id": "device-test-1",
                "tags_json": '["Животные"]',
                "client_photo_ids": ["content://photo/1"],
                "images": [self._image("dog.gif")],
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["stats"]["uploaded_count"], 1)
        self.assertEqual(response.data["photos"][0]["client_photo_id"], "content://photo/1")
        self.assertEqual(response.data["photos"][0]["face_numbers"], [1])
        self.assertEqual(ProcessedImage.objects.count(), 1)

    def test_photo_list_requires_valid_device_id(self):
        response = self.client.get("/api/photos/", {"device_id": "bad"})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["status"], "error")

    def test_photo_list_filters_by_category(self):
        ProcessedImage.objects.create(
            device_id="device-test-2",
            client_photo_id="photo-1",
            category="animals",
            tags=["dog"],
            description="A dog.",
        )
        ProcessedImage.objects.create(
            device_id="device-test-2",
            client_photo_id="photo-2",
            category="food",
            tags=["cake"],
            description="A cake.",
        )

        response = self.client.get(
            "/api/photos/",
            {"device_id": "device-test-2", "category": "animals"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["client_photo_id"], "photo-1")

    def _image(self, name: str):
        return SimpleUploadedFile(
            name,
            b"\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00"
            b"\xff\xff\xff\x21\xf9\x04\x01\x00\x00\x00\x00\x2c\x00\x00\x00\x00"
            b"\x01\x00\x01\x00\x00\x02\x02\x44\x01\x00\x3b",
            content_type="image/gif",
        )
