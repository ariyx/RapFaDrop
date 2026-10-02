from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from diagnostics.probes import classify_collection, clean_formats, soundcloud_item, spotify_artist, stable_url


class ProbeParsingTests(SimpleTestCase):
    def test_spotify_adapter_imports_with_declared_dependencies(self):
        from SpotipyFree import Spotify

        self.assertTrue(callable(Spotify))

    def test_stable_url_removes_tracking_and_fragment(self):
        url = "https://SoundCloud.com/user/track/?utm_source=x&si=secret&keep=yes#part"
        self.assertEqual(stable_url(url), "https://soundcloud.com/user/track?keep=yes")

    def test_soundcloud_output_omits_signed_format_urls(self):
        item = soundcloud_item({"id": "42", "title": "Track", "description": "remote text", "formats": [{"format_id": "http_mp3", "url": "https://signed.example/token", "ext": "mp3"}]})
        self.assertEqual(item["formats"], [{"format_id": "http_mp3", "ext": "mp3"}])
        self.assertNotIn("url", item["formats"][0])
        self.assertNotIn("description", item)
        self.assertEqual(item["description_length"], 11)

    def test_collection_without_source_type_requires_review(self):
        result = classify_collection({"title": "OCD", "description": "A collection"})
        self.assertEqual(result["classification"], "uncertain-playlist-or-release")
        self.assertEqual(result["confidence"], "review-required")

    def test_spotify_parser_keeps_ids_dates_and_pagination(self):
        client = Mock()
        client.artist.return_value = {"id": "artist", "name": "Artist"}
        client.artist_albums.return_value = {"items": [{"id": "album", "name": "Release", "album_type": "single", "release_date": "2026-01-01"}], "limit": 5, "offset": 0, "total": 1, "next": None}
        result = spotify_artist(client, "artist")
        self.assertTrue(result["observed"])
        self.assertEqual(result["recent_releases"][0]["id"], "album")
        self.assertEqual(result["pagination"]["total"], 1)

    @patch("diagnostics.probes.requests.get")
    def test_spotify_timeout_falls_back_to_partial_oembed_identity(self, get):
        client = Mock()
        client.artist.side_effect = TimeoutError("timed out")
        response = Mock(headers={})
        response.json.return_value = {"title": "Fadaei"}
        get.return_value = response
        result = spotify_artist(client, "artist", timeout=1)
        self.assertTrue(result["observed"])
        self.assertEqual(result["verification_status"], "partially-verified")
        self.assertFalse(result["capabilities"]["recent_releases"])

    def test_format_summary_preserves_audio_evidence_only(self):
        result = clean_formats([{"format_id": "hls", "acodec": "aac", "abr": 128, "url": "secret"}])
        self.assertEqual(result, [{"format_id": "hls", "acodec": "aac", "abr": 128}])
