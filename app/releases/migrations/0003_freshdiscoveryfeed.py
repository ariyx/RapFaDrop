from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):
    dependencies = [('releases', '0002_fresh_dispatch'), ('archive_collection', '0002_acquisitionsource_recordingalias')]
    operations = [migrations.CreateModel(name='FreshDiscoveryFeed', fields=[
        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
        ('enabled', models.BooleanField(default=False)), ('baseline_at', models.DateTimeField(null=True)),
        ('seen_ids', models.JSONField(default=list)), ('catchup_native_ids', models.JSONField(default=list)),
        ('next_poll_at', models.DateTimeField(default=django.utils.timezone.now)), ('last_success_at', models.DateTimeField(null=True)),
        ('consecutive_failures', models.PositiveIntegerField(default=0)), ('last_error', models.CharField(blank=True, max_length=1000)),
        ('evidence', models.JSONField(default=dict)),
        ('acquisition_source', models.OneToOneField(null=True, on_delete=django.db.models.deletion.PROTECT, to='archive_collection.acquisitionsource')),
        ('search_artist', models.OneToOneField(null=True, on_delete=django.db.models.deletion.PROTECT, to='sources.artist')),
    ])]
