import hashlib
from django.db import migrations, models


def identify_existing_fresh(apps, schema_editor):
    Candidate=apps.get_model('media_pipeline','MediaCandidate')
    for candidate in Candidate.objects.exclude(provider='manual').iterator():
        p=candidate.provenance
        if p.get('fresh_manifest_id') and p.get('native_item_id') and p.get('source_url'):
            candidate.transport_identity=hashlib.sha256((str(p['native_item_id'])+'\n'+p['source_url']).encode()).hexdigest()
            candidate.save(update_fields=('transport_identity',))


class Migration(migrations.Migration):
    dependencies=[('media_pipeline','0001_initial')]
    operations=[
        migrations.AddField(model_name='mediacandidate', name='transport_identity', field=models.CharField(blank=True, default='',max_length=64)),
        migrations.RunPython(identify_existing_fresh, migrations.RunPython.noop),
        migrations.RemoveConstraint(model_name='mediacandidate',name='media_candidate_identity_uniq'),
        migrations.AddConstraint(model_name='mediacandidate',constraint=models.UniqueConstraint(fields=('track','source_match','provider','transport_identity'),condition=~models.Q(provider='manual'),name='media_candidate_identity_uniq')),
    ]
