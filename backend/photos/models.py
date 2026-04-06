from django.db import models


class ProcessedImage(models.Model):
    image = models.ImageField(
        upload_to='images/',
        verbose_name='Изображение',
        blank=True,
        null=True
    )

    tags = models.JSONField(
        null=True,
        blank=True,
        verbose_name='Теги',
        help_text='Список тегов, полученных от нейросети'
    )

    category = models.CharField(
        max_length=100,
        verbose_name='Категория'
    )

    description = models.TextField(
        verbose_name='Описание',
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата обработки'
    )

    def __str__(self):
        return f'{self.category} ({self.created_at:%Y-%m-%d %H:%M})'

