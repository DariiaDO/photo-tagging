from django.contrib import admin
from .models import ProcessedImage

# Register your models here.

@admin.register(ProcessedImage)
class ProcessedImageAdmin(admin.ModelAdmin):
    list_display = ('id', 'category', 'created_at')
    list_filter = ('category', 'created_at')
    search_fields = ('category', 'tags')