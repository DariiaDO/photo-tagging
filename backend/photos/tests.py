from django.test import TestCase

# Create your tests here.
from django.test import SimpleTestCase

from .services.vision_api import _extract_description_from_response


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
