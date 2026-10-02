import json
from io import BytesIO
from unittest.mock import Mock, patch
from urllib.error import HTTPError, URLError

from django.test import SimpleTestCase

from .spotify_public import MAX_BYTES, combine_pages, get_public, parse_api_page, parse_html, probe_method

ARTIST = "5F0BGBdSL945Bzxrq8aGbn"
FIRST = "4shGMwLxYjEHaGqoGgbpw5"
SECOND = "5XauDXikxxSnvMfAbjUKeZ"


def response(payload, status=200):
    return {"http_status": status, "elapsed_seconds": 0.5, "rate_limit": {},
            "error": None if status == 200 else f"HTTP {status}", "body": json.dumps(payload)}


def album(item_id, date):
    return {"id": item_id, "name": "Fixture release", "album_type": "single", "release_date": date,
            "external_urls": {"spotify": "https://private.example/?token=do-not-record"}, "access_token": "do-not-record"}


class SpotifyPublicTests(SimpleTestCase):
    def test_oembed_identity_never_claims_release_discovery(self):
        result = probe_method(ARTIST, "oembed", get=Mock(return_value=response({"title": "Sijal", "html": "do-not-record"})))
        self.assertEqual(result["identity_title"], "Sijal")
        self.assertFalse(result["recent_release_listing"])
        self.assertEqual(result["items"], [])
        self.assertNotIn("do-not-record", json.dumps(result))

    def test_embed_preserves_track_order_without_inventing_dates_or_album_types(self):
        entity = {"uri": f"spotify:artist:{ARTIST}", "name": "Sijal", "accessToken": "do-not-record", "trackList": [
            {"uri": f"spotify:track:{SECOND}", "title": "Second", "audioPreview": {"url": "do-not-record"}},
            {"uri": f"spotify:track:{FIRST}", "title": "First"},
        ]}
        html = '<script id="__NEXT_DATA__">' + json.dumps({"props": {"pageProps": {"state": {"data": {"entity": entity}}}}}) + '</script>'
        result = parse_html(html, ARTIST, embedded=True)
        self.assertEqual([item["id"] for item in result["items"]], [SECOND, FIRST])
        self.assertTrue(all(item["release_date"] is None and item["release_type"] is None for item in result["items"]))
        self.assertFalse(result["recent_release_listing"])
        self.assertNotIn("do-not-record", json.dumps(result))
        with self.assertRaises(ValueError):
            parse_html(html, FIRST, embedded=True)

    def test_public_album_date_precision_and_safe_canonical_url(self):
        page = parse_api_page({"items": [album(FIRST, "2026-09"), album(SECOND, "2025")], "offset": 0, "limit": 5, "total": 2, "next": None})
        self.assertEqual(page["items"][0]["release_date_precision"], "month")
        self.assertEqual(page["items"][1]["release_date"], "2025")
        self.assertEqual(page["items"][0]["url"], f"https://open.spotify.com/album/{FIRST}")
        self.assertNotIn("do-not-record", json.dumps(page))

    def test_public_json_ld_album_is_evidence_without_proving_artist_feed_coverage(self):
        payload = {"@type": "MusicAlbum", "name": "Recent fixture", "url": f"https://open.spotify.com/album/{FIRST}?si=do-not-record", "datePublished": "2026-09-23"}
        result = parse_html('<script type="application/ld+json">' + json.dumps(payload) + '</script>', ARTIST)
        self.assertEqual(result["items"][0]["release_date"], "2026-09-23")
        self.assertIsNone(result["items"][0]["release_type"])
        self.assertFalse(result["recent_release_listing"])
        self.assertNotIn("do-not-record", json.dumps(result))

    def test_missing_stable_api_id_fails_closed(self):
        result = probe_method(ARTIST, "web-api-no-auth", get=Mock(return_value=response({"items": [{"name": "No ID"}]})))
        self.assertEqual(result["pages"][0]["error"], "unrecognized public metadata shape")
        self.assertFalse(result["recent_release_listing"])

    def test_bounded_pagination_deduplicates_without_assuming_newest_first(self):
        get = Mock(side_effect=[response({"items": [album(SECOND, "2024"), album(FIRST, "2026")], "offset": 0, "limit": 5, "total": 30, "next": "https://untrusted.example/?token=secret"}),
                                response({"items": [album(FIRST, "2026")], "offset": 5, "limit": 5, "total": 30, "next": "more"})])
        result = probe_method(ARTIST, "web-api-no-auth", get=get)
        self.assertEqual(get.call_count, 2)
        self.assertIn("offset=5", get.call_args.args[0])
        self.assertEqual([item["id"] for item in result["items"]], [SECOND, FIRST])
        self.assertTrue(result["truncated"])
        self.assertNotIn("untrusted.example", json.dumps(result))
        self.assertEqual(combine_pages([{"items": result["items"]}] * 2), result["items"])

    @patch("diagnostics.spotify_public.build_opener")
    def test_403_and_429_are_bounded_no_retry_and_numeric_retry_after_is_recorded(self, build):
        for status in (403, 429):
            with self.subTest(status=status):
                opener = Mock()
                opener.open.side_effect = HTTPError("https://open.spotify.com", status, "Forbidden", {"Retry-After": "120", "Set-Cookie": "do-not-record"}, BytesIO())
                build.return_value = opener
                result = get_public(f"https://open.spotify.com/artist/{ARTIST}", timeout=2)
                self.assertEqual(result["http_status"], status)
                self.assertEqual(result["rate_limit"], {"Retry-After": "120"})
                self.assertEqual(opener.open.call_count, 1)
                self.assertEqual(result["body"], "")
                self.assertNotIn("do-not-record", json.dumps(result))

    @patch("diagnostics.spotify_public.build_opener")
    def test_timeout_and_oversized_response_have_safe_failure(self, build):
        build.return_value.open.side_effect = URLError(TimeoutError("signed secret request"))
        result = get_public(f"https://open.spotify.com/artist/{ARTIST}")
        self.assertEqual(result["error"], "timeout")
        self.assertNotIn("secret", json.dumps(result))
        build.return_value.open.side_effect = None
        fake = build.return_value.open.return_value.__enter__.return_value = Mock(status=200, headers={})
        fake.read.return_value = b"x" * (MAX_BYTES + 1)
        self.assertEqual(get_public(f"https://open.spotify.com/artist/{ARTIST}")["error"], "invalid or oversized metadata response")

    def test_malformed_metadata_fails_without_body_or_token_leak(self):
        get = Mock(return_value={**response({}), "body": 'signed token secret'})
        result = probe_method(ARTIST, "artist-embed", get=get)
        self.assertNotIn("secret", json.dumps(result))
        # No embedded entity is not release discovery, even if HTTP was successful.
        self.assertFalse(result["recent_release_listing"])
