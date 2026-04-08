from django.db import models


class ProcessedImage(models.Model):
    device_id = models.CharField(
        max_length=100,
        verbose_name="Device ID",
        db_index=True,
    )

    client_photo_id = models.CharField(
        max_length=500,
        verbose_name="Client photo ID",
        help_text="Stable photo identifier provided by the mobile app.",
        db_index=True,
    )

    image = models.ImageField(
        upload_to="images/",
        verbose_name="Image",
        blank=True,
        null=True,
    )

    tags = models.JSONField(
        null=True,
        blank=True,
        verbose_name="Tags",
        help_text="Tags returned by the image analysis pipeline.",
    )

    category = models.CharField(
        max_length=100,
        verbose_name="Category",
    )

    description = models.TextField(
        verbose_name="Description",
        blank=True,
    )

    faces = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Faces",
        help_text="Detected faces with bounding boxes and confidence scores.",
    )

    face_count = models.PositiveIntegerField(
        default=0,
        verbose_name="Face count",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Created at",
    )

    def __str__(self):
        return f"{self.category} ({self.created_at:%Y-%m-%d %H:%M})"

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("device_id", "client_photo_id"),
                name="photos_processedimage_device_photo_unique",
            )
        ]
