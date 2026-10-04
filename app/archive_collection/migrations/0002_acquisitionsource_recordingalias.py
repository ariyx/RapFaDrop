import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('archive_collection', '0001_initial')]
    operations = [
        migrations.CreateModel(name='AcquisitionSource', fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ('platform', models.CharField(choices=[('soundcloud','SoundCloud'),('youtube','YouTube')], max_length=20)),
            ('native_id', models.CharField(max_length=160)), ('profile_url', models.URLField(max_length=500)),
            ('evidence', models.JSONField(default=dict)), ('verified_at', models.DateTimeField()),
            ('catalog', models.JSONField(default=list)), ('catalog_checked_at', models.DateTimeField(null=True)),
            ('retry_due_at', models.DateTimeField(null=True)), ('last_error', models.CharField(blank=True,max_length=1000)),
            ('artist', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,to='sources.artist')),
        ], options={'constraints':[models.UniqueConstraint(fields=('artist','platform','native_id'),name='archive_acquisition_identity_once')]}),
        migrations.CreateModel(name='RecordingAlias',fields=[
            ('id', models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name='ID')),
            ('evidence',models.JSONField(default=dict)), ('reconciled_at',models.DateTimeField(auto_now_add=True)),
            ('canonical',models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,related_name='aliases',to='archive_collection.recording')),
            ('recording',models.OneToOneField(on_delete=django.db.models.deletion.PROTECT,related_name='canonical_alias',to='archive_collection.recording')),
        ],options={'constraints':[models.CheckConstraint(condition=~models.Q(recording=models.F('canonical')),name='archive_alias_not_self')]}),
    ]
