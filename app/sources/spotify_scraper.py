"""Bounded SpotifyScraper metadata access; no audio or account features."""

import json
import re
import time
from urllib.parse import parse_qs, urlsplit

from spotify_scraper import SpotifyClient
from spotify_scraper.http.retry import RetryPolicy
from spotify_scraper.http.transport import HttpxTransport


SPOTIFY_ID = re.compile(r"[A-Za-z0-9]{22}\Z")
MAX_PAGES = 10
MAX_BYTES = 2_000_000


class SpotifyMetadataError(RuntimeError):
    """Safe, token-free source diagnostic."""

    def __init__(self, message, *, retry_after=None):
        super().__init__(message)
        self.retry_after = retry_after


class ValidatedTransport:
    """Reject incomplete discography pages before the package can flatten them."""

    def __init__(self, base=None):
        self.base = base or HttpxTransport(timeout=8, retry=RetryPolicy(max_attempts=1))
        self.total = None
        self.groups = 0
        self.pages = 0
        self.release_ids = set()
        self.requests = 0

    def get(self, url, *, headers=None):
        parts = urlsplit(url)
        if parts.scheme != "https" or parts.hostname not in {"open.spotify.com", "api-partner.spotify.com"}:
            raise SpotifyMetadataError("Unexpected Spotify metadata host")
        self.requests += 1
        if self.requests > MAX_PAGES + 4:
            raise SpotifyMetadataError("Spotify metadata request budget exceeded")
        try:
            response = self.base.get(url, headers=headers)
        except Exception as exc:
            retry_after = getattr(exc, "retry_after", None)
            raise SpotifyMetadataError(f"Spotify metadata request failed: {type(exc).__name__}", retry_after=retry_after) from None
        if response.status_code != 200:
            retry_after = None
            if response.status_code == 429:
                try:
                    retry_after = int(response.headers.get("Retry-After", ""))
                except ValueError:
                    pass
            raise SpotifyMetadataError(f"Spotify metadata HTTP {response.status_code}", retry_after=retry_after)
        if len(response.content) > MAX_BYTES:
            raise SpotifyMetadataError("Spotify metadata response exceeds byte limit")
        if parts.hostname == "api-partner.spotify.com":
            query = parse_qs(parts.query)
            if query.get("operationName") == ["queryArtistDiscographyAll"]:
                self._validate_page(response, query)
        return response

    def _validate_page(self, response, query):
        self.pages += 1
        if self.pages > MAX_PAGES:
            raise SpotifyMetadataError("Spotify discography page budget exceeded")
        try:
            variables = json.loads(query["variables"][0])
            offset, limit = variables["offset"], variables["limit"]
            body = response.json()
            section = body["data"]["artistUnion"]["discography"]["all"]
            total, groups = section["totalCount"], section["items"]
        except (KeyError, IndexError, TypeError, ValueError, AttributeError):
            raise SpotifyMetadataError("Spotify discography page has missing or malformed fields") from None
        if (type(total) is not int or total < 0 or type(offset) is not int or
                type(limit) is not int or limit != 50 or offset != self.groups or
                not isinstance(groups, list) or len(groups) != min(limit, total - offset) or
                (self.total is not None and total != self.total)):
            raise SpotifyMetadataError("Spotify discography total, offset, or page length is inconsistent")
        if self.total is None:
            self.total = total
        for group in groups:
            if not isinstance(group, dict) or not isinstance(group.get("releases"), dict):
                raise SpotifyMetadataError("Spotify discography release group is incomplete")
            releases = group["releases"].get("items")
            if not isinstance(releases, list) or not releases:
                raise SpotifyMetadataError("Spotify discography release group is empty")
            for release in releases:
                if not isinstance(release, dict):
                    raise SpotifyMetadataError("Spotify discography release is malformed")
                uri = release.get("uri")
                native_id = uri.removeprefix("spotify:album:") if isinstance(uri, str) and uri.startswith("spotify:album:") else ""
                if not SPOTIFY_ID.fullmatch(native_id) or not isinstance(release.get("name"), str) or not release["name"].strip():
                    raise SpotifyMetadataError("Spotify discography release lacks stable ID or title")
                if native_id in self.release_ids:
                    raise SpotifyMetadataError("Spotify discography repeats a release ID")
                self.release_ids.add(native_id)
        self.groups += len(groups)

    def finish(self, releases):
        if self.total is None or self.groups != self.total or len(releases) != len(self.release_ids):
            raise SpotifyMetadataError("Spotify discography was not fully validated")

    def close(self):
        self.base.close()


def _profile_id(source):
    native_id = source.native_profile_id
    if not SPOTIFY_ID.fullmatch(native_id or ""):
        raise SpotifyMetadataError("Spotify source has no valid native artist ID")
    if source.canonical_url != f"https://open.spotify.com/artist/{native_id}":
        raise SpotifyMetadataError("Spotify source URL does not match its native artist ID")
    return native_id


def _release_item(release, artist_id):
    native_id = release.id
    if not SPOTIFY_ID.fullmatch(native_id or ""):
        raise SpotifyMetadataError("Spotify release has no stable ID")
    safe = {"artist_id": artist_id, "release_id": native_id, "release_title": release.name}
    return {
        "native_item_id": native_id,
        "title": str(release.name)[:500],
        "canonical_url": f"https://open.spotify.com/album/{native_id}",
        "source_release_at": None,
        "metadata": {"spotify_discovery": True, "artist_id": artist_id},
        "sanitized_raw_data": safe,
    }


class SpotifyScraperDiscovery:
    platform = "spotify"

    def __init__(self, client_factory=SpotifyClient, transport_factory=ValidatedTransport):
        self.client_factory = client_factory
        self.transport_factory = transport_factory
        self.last_probe = None

    def resolve_profile(self, source):
        native_id = _profile_id(source)
        transport = self.transport_factory()
        started = time.monotonic()
        try:
            with self.client_factory(transport=transport) as client:
                artist = client.get_artist(native_id)
            if artist.id != native_id or not artist.name:
                raise SpotifyMetadataError("Spotify artist identity mismatch")
            return {"id": artist.id, "name": artist.name}
        except SpotifyMetadataError:
            raise
        except Exception as exc:
            raise SpotifyMetadataError(f"Spotify artist identity request failed: {type(exc).__name__}") from None
        finally:
            self.last_probe = {"requests": transport.requests, "pages": transport.pages, "elapsed_seconds": round(time.monotonic() - started, 3)}
            transport.close()

    def list_recent(self, source):
        native_id = _profile_id(source)
        transport = self.transport_factory()
        started = time.monotonic()
        try:
            with self.client_factory(transport=transport) as client:
                releases = client.get_discography(native_id)
            transport.finish(releases)
            return [_release_item(release, native_id) for release in releases]
        except SpotifyMetadataError:
            raise
        except Exception as exc:
            raise SpotifyMetadataError(f"Spotify discography request failed: {type(exc).__name__}") from None
        finally:
            self.last_probe = {"requests": transport.requests, "pages": transport.pages, "elapsed_seconds": round(time.monotonic() - started, 3)}
            transport.close()

    def fetch_item(self, source, item):
        native_id = item["native_item_id"]
        if not SPOTIFY_ID.fullmatch(native_id):
            raise SpotifyMetadataError("Spotify release ID is invalid")
        transport = self.transport_factory()
        started = time.monotonic()
        try:
            with self.client_factory(transport=transport) as client:
                album = client.get_album(native_id)
            if album.id != native_id:
                raise SpotifyMetadataError("Spotify release detail ID mismatch")
            album_type = str(album.album_type or "").lower()
            if album_type not in {"single", "album", "ep"}:
                album_type = ""
            artists = [str(artist.name)[:200] for artist in album.artists]
            if (not isinstance(album.total_tracks, int) or album.total_tracks < 1 or
                    album.total_tracks > 100 or len(album.tracks) != album.total_tracks):
                raise SpotifyMetadataError("Spotify release track list is incomplete or exceeds the pilot limit")
            tracks = []
            for position, track in enumerate(album.tracks, 1):
                if not SPOTIFY_ID.fullmatch(track.id or "") or not track.name or track.duration_ms <= 0:
                    raise SpotifyMetadataError("Spotify release track lacks stable ID, title, or duration")
                tracks.append({"id": track.id, "title": str(track.name)[:500],
                               "position": position, "duration_seconds": round(track.duration_ms / 1000, 3),
                               "artist_credits": [str(credit.name)[:200] for credit in track.artists]})
            item["source_release_at"] = album.release_date
            item["metadata"].update({"album_type": album_type, "album": album.name if album_type in {"album", "ep"} else "", "artist_credits": artists, "track_count": len(album.tracks), "tracks": tracks})
            item["sanitized_raw_data"].update({"album_type": album_type or None, "release_date": album.release_date.isoformat() if album.release_date else None, "artist_credits": artists, "track_count": len(album.tracks), "tracks": tracks})
            return item
        except SpotifyMetadataError:
            raise
        except Exception as exc:
            raise SpotifyMetadataError(f"Spotify release detail request failed: {type(exc).__name__}") from None
        finally:
            self.last_probe = {"requests": transport.requests, "pages": transport.pages, "elapsed_seconds": round(time.monotonic() - started, 3)}
            transport.close()
