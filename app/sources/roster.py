"""Offline owner-approved roster import. Never polls or resets operational state."""

import json
import re
from pathlib import Path
from urllib.parse import urlsplit

from django.db import transaction

from releases.normalization import normalize_text
from .models import Artist, ArtistSource, SourceAuditEvent


MANIFEST = Path(__file__).with_name('data') / 'approved_roster.json'


class RosterConflict(ValueError):
    """Import must stop rather than merge ambiguous identities."""


def load_roster():
    return json.loads(MANIFEST.read_text(encoding='utf-8'))


def _profile_key(platform, url):
    return url.rstrip('/').casefold() if platform == 'soundcloud' else url.rstrip('/')


def validate_roster(rows):
    names, profiles = set(), set()
    for row in rows:
        name = normalize_text(row['official_name'])
        if not name or name in names:
            raise RosterConflict('Empty or duplicate roster identity')
        names.add(name)
        if not isinstance(row['aliases'], list) or not all(isinstance(a, str) for a in row['aliases']):
            raise RosterConflict('Invalid roster aliases')
        for platform, candidate in row['sources'].items():
            url, native_id = candidate['url'], candidate.get('native_profile_id', '')
            parts = urlsplit(url)
            valid = parts.scheme == 'https' and not parts.query and not parts.fragment
            if platform == 'spotify':
                valid &= parts.netloc == 'open.spotify.com' and bool(re.fullmatch(r'[A-Za-z0-9]{22}', native_id)) and parts.path == '/artist/' + native_id
            elif platform == 'soundcloud':
                valid &= parts.netloc == 'soundcloud.com' and bool(re.fullmatch(r'/[A-Za-z0-9_-]+', parts.path))
            else:
                valid = False
            key = (platform, _profile_key(platform, url))
            if not valid or key in profiles:
                raise RosterConflict('Invalid or duplicate roster profile')
            profiles.add(key)
            outcome = candidate.get('verification', {})
            if not candidate.get('provenance') or not outcome.get('outcome'):
                raise RosterConflict('Candidate lacks provenance or verification outcome')
            if outcome['outcome'] == 'verified' and not (
                outcome.get('identity_confirmed') and outcome.get('adapter_success') and outcome.get('evidence')
            ):
                raise RosterConflict('Verified candidate lacks identity and adapter evidence')


def _find_artist(row):
    """Reuse contributors and curated names by aliases or native profile identity."""
    matches = set()
    names = {normalize_text(value) for value in [row['official_name'], *row['aliases']]}
    for artist in Artist.objects.select_for_update().all():
        if names & {normalize_text(value) for value in [artist.official_name, *(artist.aliases or [])]}:
            matches.add(artist.pk)
    for platform, candidate in row['sources'].items():
        for source in ArtistSource.objects.filter(platform=platform):
            if (_profile_key(platform, source.canonical_url) == _profile_key(platform, candidate['url']) or
                    candidate.get('native_profile_id') and source.native_profile_id == candidate['native_profile_id']):
                matches.add(source.artist_id)
    if len(matches) > 1:
        raise RosterConflict(f"Ambiguous existing identity for {row['official_name']}")
    return Artist.objects.get(pk=next(iter(matches))) if matches else None


@transaction.atomic
def import_roster(rows=None, *, dry_run=False):
    rows = load_roster() if rows is None else rows
    validate_roster(rows)
    result = {'approved_identities': len(rows), 'artists_created': 0, 'artists_reused': 0,
              'sources_created': 0, 'sources_preserved': 0, 'curated_differences': [], 'identities': []}
    # Serialize repeated/concurrent imports without changing a production source.
    from django.db import connection
    with connection.cursor() as cursor:
        cursor.execute('SELECT pg_advisory_xact_lock(%s)', [830041])
    for row in rows:
        artist = _find_artist(row)
        if artist is None:
            artist = Artist.objects.create(official_name=row['official_name'], aliases=list(row['aliases']), enabled=False)
            result['artists_created'] += 1
        else:
            result['artists_reused'] += 1
            aliases = list(artist.aliases or [])
            for alias in [row['official_name'], *row['aliases']]:
                if alias != artist.official_name and alias not in aliases:
                    aliases.append(alias)
            if aliases != artist.aliases:
                artist.aliases = aliases
                artist.save(update_fields=('aliases', 'updated_at'))
        result['identities'].append({'name': row['official_name'], 'artist_id': artist.pk})
        for platform, candidate in row['sources'].items():
            source, created = ArtistSource.objects.get_or_create(
                artist=artist, platform=platform,
                defaults={'canonical_url': candidate['url'], 'native_profile_id': candidate.get('native_profile_id', ''),
                          'enabled': False, 'verification': ('verified' if candidate['verification']['outcome'] == 'verified' else 'unverified')},
            )
            if created:
                result['sources_created'] += 1
                SourceAuditEvent.objects.create(source=source, artist=artist, event_type='roster_candidate_added', detail=candidate)
            else:
                result['sources_preserved'] += 1
                if source.canonical_url != candidate['url'] or (candidate.get('native_profile_id') and source.native_profile_id != candidate['native_profile_id']):
                    result['curated_differences'].append({'artist_id': artist.pk, 'platform': platform})
    if len({identity['artist_id'] for identity in result['identities']}) != len(rows):
        raise RosterConflict('Multiple approved identities resolve to one artist')
    SourceAuditEvent.objects.create(event_type='seed_imported', detail={k: v for k, v in result.items() if k != 'identities'})
    if dry_run:
        transaction.set_rollback(True)
    return result
