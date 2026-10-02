"""Opt-in public metadata experiments; never imported by polling adapters.

No credentials, browser automation, cookies, token extraction or media requests.
Only allowlisted metadata is returned; raw HTML/JSON is never recorded.
"""
import json
import re
import socket
import time
from datetime import datetime, timezone
from html.parser import HTMLParser
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


ID = re.compile(r"[A-Za-z0-9]{22}\Z")
MAX_BYTES = 1024 * 1024
METHODS = ("oembed", "artist-page", "artist-embed", "web-api-no-auth")


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None  # A login/challenge redirect is evidence, not an invitation.


def get_public(url, timeout=12):
    """One bounded GET, no session/cookie jar and no automatic retries."""
    parts = urlsplit(url)
    if parts.scheme != "https" or parts.hostname not in {"open.spotify.com", "api.spotify.com"}:
        raise ValueError("Only public Spotify metadata hosts are allowed")
    started = time.monotonic()
    result = {"http_status": None, "rate_limit": {}, "body": "", "error": None}
    try:
        request = Request(url, headers={"User-Agent": "RapFaDrop-feasibility/1.0", "Accept": "text/html,application/json"})
        with build_opener(NoRedirect()).open(request, timeout=timeout) as response:
            result["http_status"] = response.status
            body = response.read(MAX_BYTES + 1)
            if len(body) > MAX_BYTES:
                raise ValueError("Response exceeds metadata byte bound")
            result["body"] = body.decode("utf-8")
            result["rate_limit"] = rate_headers(response.headers)
    except HTTPError as exc:
        result.update(http_status=exc.code, rate_limit=rate_headers(exc.headers), error=f"HTTP {exc.code}")
        exc.close()
    except (TimeoutError, socket.timeout):
        result["error"] = "timeout"
    except URLError as exc:
        result["error"] = "timeout" if isinstance(exc.reason, (TimeoutError, socket.timeout)) else "network unavailable"
    except (ValueError, UnicodeError):
        result["error"] = "invalid or oversized metadata response"
    result["elapsed_seconds"] = round(time.monotonic() - started, 3)
    return result


def rate_headers(headers):
    # Retain only numeric public limits; never copy cookies or authentication headers.
    return {key: str(headers[key])[:20] for key in ("Retry-After", "X-RateLimit-Limit", "X-RateLimit-Remaining")
            if headers.get(key) and re.fullmatch(r"[0-9.]+", str(headers[key]))}


def native_id(value, kind):
    value = str(value or "")
    if ID.fullmatch(value):
        return value
    prefix = f"spotify:{kind}:"
    if value.startswith(prefix) and ID.fullmatch(value[len(prefix):]):
        return value[len(prefix):]
    parts = urlsplit(value)
    match = re.fullmatch(rf"/{kind}/([A-Za-z0-9]{{22}})/?", parts.path)
    if parts.scheme == "https" and parts.hostname == "open.spotify.com" and match:
        return match[1]
    return None


def public_item(value, kind="album"):
    item_id = native_id(value.get("id") or value.get("uri") or value.get("url"), kind)
    if not item_id:
        raise ValueError("No stable Spotify item ID")
    date = value.get("release_date") or value.get("releaseDate") or value.get("datePublished")
    # Preserve date precision; never invent a day or derive a date from popularity order.
    if not isinstance(date, str) or not re.fullmatch(r"\d{4}(?:-\d{2}(?:-\d{2})?)?", date):
        date = None
    return {"id": item_id, "title": str(value.get("name") or value.get("title") or "")[:500],
            "object_type": kind, "release_type": value.get("album_type") if value.get("album_type") in {"album", "single", "compilation"} else None,
            "release_date": date, "release_date_precision": ({4: "year", 7: "month", 10: "day"}.get(len(date)) if date else None),
            "url": f"https://open.spotify.com/{kind}/{item_id}"}


def parse_api_page(payload):
    """A fixture-tested future API shape, not an authenticated production adapter."""
    if not isinstance(payload.get("items"), list):
        raise ValueError("No release page")
    items = [public_item(value) for value in payload["items"]]
    return {"items": items, "pagination": {key: payload.get(key) for key in ("offset", "limit", "total")},
            "has_next": bool(payload.get("next")), "order": "provider page order; newest-first not assumed"}


def combine_pages(pages):
    """Deduplicate stable IDs across bounded pages, preserving provider order."""
    result = []
    seen = set()
    for page in pages:
        for item in page["items"]:
            if item["id"] not in seen:
                result.append(item)
                seen.add(item["id"])
    return result


class PublicHTML(HTMLParser):
    def __init__(self):
        super().__init__()
        self.title = ""
        self.scripts = []
        self.links = []
        self.script_kind = None
        self.script = ""

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "meta" and attrs.get("property") == "og:title":
            self.title = attrs.get("content", "")[:500]
        if tag == "a" and attrs.get("href"):
            self.links.append(attrs["href"])
        if tag == "script":
            self.script_kind = "next" if attrs.get("id") == "__NEXT_DATA__" else "ld" if attrs.get("type") == "application/ld+json" else None
            self.script = ""

    def handle_data(self, data):
        if self.script_kind:
            self.script += data

    def handle_endtag(self, tag):
        if tag == "script" and self.script_kind:
            self.scripts.append((self.script_kind, json.loads(self.script)))
            self.script_kind = None


def parse_html(body, artist_id, embedded=False):
    parser = PublicHTML()
    parser.feed(body)
    result = {"identity_title": parser.title or None, "items": [], "pagination": {}, "has_next": False,
              "order": "public page subset; release chronology unproven", "recent_release_listing": False}
    if embedded:
        for kind, data in parser.scripts:
            if kind != "next":
                continue
            entity = data.get("props", {}).get("pageProps", {}).get("state", {}).get("data", {}).get("entity", {})
            if native_id(entity.get("uri") or entity.get("id"), "artist") != artist_id:
                raise ValueError("Embed artist mismatch")
            result["identity_title"] = str(entity.get("name") or entity.get("title") or "")[:500]
            result["items"] = [public_item(track, "track") for track in entity.get("trackList", [])]
            result["order"] = "embed trackList order; not a recent-release feed"
    else:
        # JSON-LD MusicAlbum evidence may supply dates; links alone cannot.
        for kind, data in parser.scripts:
            if kind != "ld":
                continue
            nodes = data if isinstance(data, list) else data.get("@graph", [data])
            for node in nodes:
                if node.get("@type") == "MusicAlbum":
                    result["items"].append(public_item(node))
        seen = {item["id"] for item in result["items"]}
        for link in parser.links:
            item_id = native_id(link, "album")
            if item_id and item_id not in seen:
                result["items"].append(public_item({"id": item_id}))
                seen.add(item_id)
    return result


def probe_method(artist_id, method, timeout=12, get=get_public):
    if not ID.fullmatch(artist_id) or method not in METHODS:
        raise ValueError("Invalid artist ID or method")
    base = f"https://open.spotify.com/artist/{artist_id}"
    urls = {"oembed": "https://open.spotify.com/oembed?" + urlencode({"url": base}),
            "artist-page": base, "artist-embed": f"https://open.spotify.com/embed/artist/{artist_id}",
            "web-api-no-auth": f"https://api.spotify.com/v1/artists/{artist_id}/albums?" + urlencode({"include_groups": "album,single", "market": "US", "limit": 5, "offset": 0})}
    result = {"artist_id": artist_id, "method": method, "url": urls[method],
              "observed_at": datetime.now(timezone.utc).isoformat(), "items": [], "identity_title": None,
              "recent_release_listing": False, "pages": [], "order": "unavailable", "pagination": {}}
    pages = []
    for offset in (0, 5):
        url = urls[method] if not offset else urls[method].replace("offset=0", "offset=5")
        response = get(url, timeout=timeout)
        result["pages"].append({key: response[key] for key in ("http_status", "elapsed_seconds", "rate_limit", "error")})
        if response["error"] or response["http_status"] != 200:
            break
        try:
            if method == "oembed":
                result.update(identity_title=str(json.loads(response["body"]).get("title") or "")[:500], order="identity only; no release listing")
                break
            if method in {"artist-page", "artist-embed"}:
                result.update(parse_html(response["body"], artist_id, embedded=method == "artist-embed"))
                break
            page = parse_api_page(json.loads(response["body"]))
            pages.append(page)
            result.update(items=combine_pages(pages), pagination=page["pagination"], order=page["order"],
                          recent_release_listing=True, truncated=page["has_next"])
            if not page["has_next"]:
                break
        except (ValueError, TypeError, AttributeError, KeyError):
            result["pages"][-1]["error"] = "unrecognized public metadata shape"
            break
    result["elapsed_seconds"] = round(sum(page["elapsed_seconds"] for page in result["pages"]), 3)
    return result
