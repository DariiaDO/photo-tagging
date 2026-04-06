from rest_framework.views import APIView
from rest_framework.response import Response

from .models import ProcessedImage
from .services.vision_api import analyze_image_llava as analyze_image




class ImageUploadView(APIView):
    """
    Принимает изображение от мобильного приложения,
    отправляет его в нейросеть и сохраняет результат в БД
    """

    def post(self, request):
        images = request.FILES.getlist('images')
        if not images:
            return Response({"detail": "No images were provided. Use field name 'images'."}, status=400)

        # Optional client-side ids to bind response rows to sender DB records.
        # Expected format: multipart field `client_photo_ids` repeated N times.
        client_photo_ids = request.data.getlist("client_photo_ids")
        results = []

        for index, image_file in enumerate(images):
            processed_image = ProcessedImage.objects.create(image=image_file)

            image_path = processed_image.image.path
            try:
                result = analyze_image(image_path)
            except Exception as exc:
                result = {
                    "tags": [],
                    "category": "unknown",
                    "description": f"LLaVA error: {exc}",
                }

            processed_image.tags = result.get("tags", [])
            processed_image.category = result.get("category", "unknown")
            processed_image.description = result.get("description", "")
            processed_image.save()

            client_photo_id = None
            if index < len(client_photo_ids):
                value = str(client_photo_ids[index]).strip()
                client_photo_id = value or None

            results.append({
                "id": processed_image.id,
                "upload_index": index,
                "client_photo_id": client_photo_id,
                "original_filename": image_file.name,
                "image_url": processed_image.image.url if processed_image.image else None,
                "tags": processed_image.tags,
                "category": processed_image.category,
                "description": processed_image.description,
            })

        return Response(results)
