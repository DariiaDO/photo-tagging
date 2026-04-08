from django.db import migrations, models


def backfill_legacy_photo_ids(apps, schema_editor):
    ProcessedImage = apps.get_model('photos', 'ProcessedImage')
    for photo in ProcessedImage.objects.all().iterator():
        if not photo.device_id:
            photo.device_id = 'legacy-device'
        if not photo.client_photo_id:
            photo.client_photo_id = f'legacy-{photo.pk}'
        photo.save(update_fields=['device_id', 'client_photo_id'])


class Migration(migrations.Migration):

    dependencies = [
        ('photos', '0004_alter_processedimage_category_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='processedimage',
            name='client_photo_id',
            field=models.CharField(
                db_index=True,
                default='',
                help_text='Stable photo identifier provided by the mobile app.',
                max_length=500,
                verbose_name='Client photo ID',
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='processedimage',
            name='device_id',
            field=models.CharField(
                db_index=True,
                default='legacy-device',
                max_length=100,
                verbose_name='Device ID',
            ),
            preserve_default=False,
        ),
        migrations.RunPython(backfill_legacy_photo_ids, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name='processedimage',
            constraint=models.UniqueConstraint(
                fields=('device_id', 'client_photo_id'),
                name='photos_processedimage_device_photo_unique',
            ),
        ),
    ]
