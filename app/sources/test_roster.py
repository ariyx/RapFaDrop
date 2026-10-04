from copy import deepcopy
from django.test import TestCase
from django.utils import timezone

from sources.models import Artist, ArtistSource, SourceAuditEvent
from sources.roster import RosterConflict, import_roster, load_roster


def candidate(name='Artist', alias='هنرمند', native_id='A' * 22):
    return {'official_name': name, 'aliases': [alias], 'sources': {'spotify': {
        'url': 'https://open.spotify.com/artist/' + native_id, 'native_profile_id': native_id,
        'provenance': 'Owner supplied', 'verification': {'outcome': 'unverified'}}}}


class RosterTests(TestCase):
    def test_reuses_contributor_by_platform_id_and_preserves_curated_artist_name(self):
        artist = Artist.objects.create(official_name='Curated artist', aliases=['custom'])
        source = ArtistSource.objects.create(artist=artist, platform='spotify', native_profile_id='A' * 22,
                                            canonical_url='https://open.spotify.com/artist/' + 'A' * 22)
        result = import_roster([candidate()])
        self.assertEqual(result['artists_created'], 0)
        artist.refresh_from_db()
        self.assertEqual(artist.official_name, 'Curated artist')
        self.assertEqual(artist.aliases, ['custom', 'Artist', 'هنرمند'])
        self.assertEqual(ArtistSource.objects.get().pk, source.pk)

    def test_reuses_persian_alias_with_half_space_normalization(self):
        artist = Artist.objects.create(official_name='Curated', aliases=['علی‌قاف'])
        result = import_roster([candidate(alias='علی قاف')])
        self.assertEqual(result['identities'][0]['artist_id'], artist.pk)
        self.assertEqual(Artist.objects.count(), 1)

    def test_repeated_import_preserves_all_active_source_fields_and_aliases(self):
        artist = Artist.objects.create(official_name='Artist', aliases=['owner alias'], enabled=True)
        source = ArtistSource.objects.create(artist=artist, platform='spotify', native_profile_id='curated-id',
            canonical_url='https://open.spotify.com/artist/curated-profile', enabled=True, verification='verified',
            baseline_started_at=timezone.now(), baseline_completed_at=timezone.now(),
            last_success_at=timezone.now(), next_poll_at=timezone.now(), poll_interval_seconds=180,
            consecutive_failures=2, last_error='old diagnostic', last_error_at=timezone.now())
        before = ArtistSource.objects.values().get(pk=source.pk)
        import_roster([candidate()])
        result = import_roster([candidate()])
        self.assertEqual(result['artists_created'], 0)
        self.assertEqual(result['sources_created'], 0)
        self.assertEqual(ArtistSource.objects.values().get(pk=source.pk), before)
        artist.refresh_from_db()
        self.assertTrue(artist.enabled)
        self.assertIn('owner alias', artist.aliases)

    def test_ambiguous_name_and_native_id_abort_every_change(self):
        first = Artist.objects.create(official_name='Artist')
        other = Artist.objects.create(official_name='Different')
        ArtistSource.objects.create(artist=other, platform='spotify', native_profile_id='A' * 22)
        with self.assertRaises(RosterConflict):
            import_roster([candidate(name='New', native_id='B' * 22), candidate()])
        self.assertEqual(Artist.objects.count(), 2)
        self.assertFalse(SourceAuditEvent.objects.exists())
        self.assertEqual(Artist.objects.get(pk=first.pk).aliases, [])

    def test_dry_run_has_no_writes(self):
        result = import_roster([candidate()], dry_run=True)
        self.assertEqual(result['artists_created'], 1)
        self.assertEqual(Artist.objects.count(), 0)
        self.assertEqual(ArtistSource.objects.count(), 0)
        self.assertEqual(SourceAuditEvent.objects.count(), 0)

    def test_verified_without_adapter_evidence_is_rejected(self):
        row = candidate()
        row['sources']['spotify']['verification']['outcome'] = 'verified'
        with self.assertRaises(RosterConflict):
            import_roster([row])

    def test_album_url_cannot_be_a_profile(self):
        row = candidate()
        row['sources']['spotify']['url'] = 'https://open.spotify.com/album/' + 'A' * 22
        with self.assertRaises(RosterConflict):
            import_roster([row])

    def test_full_roster_remains_disabled_and_replay_creates_nothing(self):
        rows = load_roster()
        self.assertEqual(len(rows), 83)
        result = import_roster(rows)
        self.assertEqual(result['artists_created'], 83)
        self.assertFalse(Artist.objects.filter(enabled=True).exists())
        self.assertFalse(ArtistSource.objects.filter(enabled=True).exists())
        second = import_roster(rows)
        self.assertEqual(second['artists_created'], 0)
        self.assertEqual(second['sources_created'], 0)
        self.assertEqual(Artist.objects.count(), 83)
        for row in rows:
            self.assertIn(row['persian_name'], Artist.objects.get(official_name=row['official_name']).aliases)
