from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('photos', '0005_processedimage_client_photo_id_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='FaceIdentity',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('device_id', models.CharField(db_index=True, max_length=100, verbose_name='Device ID')),
                ('number', models.PositiveIntegerField(verbose_name='Face number')),
                ('embedding', models.JSONField(blank=True, default=list, help_text='Normalized embedding used to match faces across photos.', verbose_name='Face embedding')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created at')),
            ],
            options={
                'ordering': ('number',),
            },
        ),
        migrations.AddConstraint(
            model_name='faceidentity',
            constraint=models.UniqueConstraint(fields=('device_id', 'number'), name='photos_faceidentity_device_number_unique'),
        ),
    ]
