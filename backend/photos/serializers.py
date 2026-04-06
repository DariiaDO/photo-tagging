from rest_framework import serializers
from .models import ProcessedImage


class ImageUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProcessedImage
        fields = ('id', 'image')
