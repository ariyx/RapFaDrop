"""Strict artist-specific Spotify web-player Top Tracks, never an embed fallback."""
import time
from datetime import datetime, timezone

from spotify_scraper import SpotifyClient
from sources.spotify_scraper import ValidatedTransport, SpotifyMetadataError, SPOTIFY_ID, _profile_id


class PopularTransport(ValidatedTransport):
    def __init__(self, base=None):
        super().__init__(base)
        self.artist_union = None
        self.endpoint = ""

    def get(self, url, *, headers=None):
        response = super().get(url, headers=headers)
        if "api-partner.spotify.com" in url and "queryArtistOverview" in url:
            self.artist_union = response.json().get("data", {}).get("artistUnion")
            self.endpoint = "https://api-partner.spotify.com/pathfinder/v1/query?operationName=queryArtistOverview"
        return response


def validate_popular(raw, artist_id):
    if not isinstance(raw, dict) or raw.get("uri") != f"spotify:artist:{artist_id}":
        raise SpotifyMetadataError("Popular artist identity is missing or mismatched")
    name = raw.get("profile", {}).get("name")
    section = raw.get("discography", {}).get("topTracks")
    if not name or not isinstance(section, dict) or not isinstance(section.get("items"), list):
        raise SpotifyMetadataError("Complete Popular section unavailable; embed subsets are not accepted")
    rows = section["items"]
    if not rows or len(rows) > 10 or ("totalCount" in section and section["totalCount"] != len(rows)):
        raise SpotifyMetadataError("Popular section is empty, partial or exceeds ten-track contract")
    tracks, ids = [], set()
    for rank, row in enumerate(rows, 1):
        try:
            track = row["track"]
            native = track["id"]
            credits = [{"id": credit["uri"].removeprefix("spotify:artist:"), "name": credit["profile"]["name"]}
                       for credit in track["artists"]["items"]]
            duration = track["duration"]["totalMilliseconds"] / 1000
            album_id = track["albumOfTrack"]["uri"].removeprefix("spotify:album:")
            playable = track["playability"]["playable"]
            title = track["name"]
        except (KeyError, TypeError, AttributeError):
            raise SpotifyMetadataError("Popular entry is incomplete") from None
        if (not SPOTIFY_ID.fullmatch(native) or track.get("uri") != f"spotify:track:{native}" or native in ids or not title or duration <= 0 or
                not SPOTIFY_ID.fullmatch(album_id) or not credits or
                any(not SPOTIFY_ID.fullmatch(c["id"]) or not c["name"] for c in credits) or type(playable) is not bool):
            raise SpotifyMetadataError("Popular entry lacks a unique stable identity, credits or duration")
        ids.add(native)
        tracks.append({"id": native, "rank": rank, "title": title, "credits": credits,
                       "duration_seconds": duration, "album_id": album_id,
                       "disc_number": track.get("discNumber", 1), "playable": playable,
                       "spotify_url": f"https://open.spotify.com/track/{native}"})
    return name, tracks


def fetch_popular(source):
    artist_id = _profile_id(source)
    started = time.monotonic()
    transport = PopularTransport()
    try:
        with SpotifyClient(transport=transport) as client:
            artist = client.get_artist(artist_id)
            name, tracks = validate_popular(transport.artist_union, artist_id)
            if artist.id != artist_id or artist.name != name:
                raise SpotifyMetadataError("Popular parsed/raw artist mismatch")
            selected, skipped = select_two(tracks, artist_id)
            albums = {}
            for row in selected:
                if row["album_id"] not in albums:
                    albums[row["album_id"]] = client.get_album(row["album_id"])
                album = albums[row["album_id"]]
                members = [t for t in album.tracks if t.id == row["id"]]
                if album.id != row["album_id"] or len(album.tracks) != album.total_tracks or len(members) != 1:
                    raise SpotifyMetadataError("Selected track's album metadata is incomplete")
                member = members[0]
                if member.name != row["title"] or abs(member.duration_ms / 1000 - row["duration_seconds"]) > 1:
                    raise SpotifyMetadataError("Popular and album recording metadata conflict")
                row.update(album_title=album.name, track_number=member.track_number,
                           release_date=album.release_date.date().isoformat() if album.release_date else None,
                           artwork_url=album.images[0].url if album.images else "",
                           album_type=str(album.album_type), album_artists=[a.name for a in album.artists])
        return {"artist_id": artist_id, "artist_name": name, "provider": "SpotifyScraper 3.9.2",
                "endpoint": transport.endpoint, "ordering": "artistUnion.discography.topTracks.items (returned order)",
                "market": "not explicitly supplied; anonymous server session", "observed_at": datetime.now(timezone.utc).isoformat(),
                "tracks": tracks, "selected": selected, "skipped": skipped,
                "requests": transport.requests, "discovery_seconds": round(time.monotonic() - started, 3)}
    except Exception as exc:
        error = SpotifyMetadataError(str(exc)) if isinstance(exc, SpotifyMetadataError) else SpotifyMetadataError(f"Popular metadata failed: {type(exc).__name__}")
        error.probe = {"requests": transport.requests, "discovery_seconds": round(time.monotonic() - started, 3),
                       "artist_id": artist_id, "endpoint": transport.endpoint}
        raise error from None
    finally:
        transport.close()


def select_two(tracks, artist_id):
    selected, skipped = [], []
    for row in tracks:
        if artist_id not in [c["id"] for c in row["credits"]]:
            skipped.append({"rank": row["rank"], "id": row["id"], "reason": "verified artist not credited"})
        elif not row["playable"]:
            skipped.append({"rank": row["rank"], "id": row["id"], "reason": "Spotify reports this recording unplayable in the observed session"})
        else:
            selected.append(dict(row))
            if len(selected) == 2:
                break
    return selected, skipped
