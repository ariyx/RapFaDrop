import re
from dataclasses import dataclass
from html import escape, unescape
from urllib.parse import parse_qsl, urlsplit


class CaptionError(ValueError):
    pass


DEFAULT_CONFIG = {
    "header": "DROP", "lp_header": "LP DROP", "ep_header": "EP DROP",
    "footer": "t.me/RapFaDrop", "intro_footer": "t.me/RapFaDrop",
    "prior_heading": "پیش‌تر از این آلبوم منتشر شده:",
    "rows": ["music_video_url", "album_post_url", "original_track_post_url", "platforms"],
    "labels": {"music_video_url": "Music Video", "spotify_url": "Spotify", "soundcloud_url": "SoundCloud", "album_post_url": "Album", "original_track_post_url": "Original", "original_album_post_url": "Original Album"},
}


@dataclass(frozen=True)
class RenderedCaption:
    html: str
    overflow: tuple = ()


def visible_length(value):
    # UTF-16 counting is conservative for astral characters and matches entity offsets.
    plain = unescape(re.sub(r"<[^>]*>", "", value))
    return len(plain.encode("utf-16-le")) // 2


def safe_url(value, *, channel=False):
    value = str(value or "").strip()
    parts = urlsplit(value)
    if not value:
        return ""
    if parts.scheme != "https" or not parts.hostname or parts.username or parts.password or any(ord(char) < 32 for char in value):
        raise CaptionError("Links require a valid HTTPS URL without credentials")
    if channel and parts.hostname.lower() != "t.me":
        raise CaptionError("Publication links must point to a stored Telegram URL")
    secret_keys = {"token", "access_token", "auth", "authorization", "key", "api_key", "sig", "signature", "policy", "__token__"}
    if any(key.lower() in secret_keys or key.lower().startswith("x-amz-") for key, _ in parse_qsl(parts.query)):
        raise CaptionError("Signed or credential-bearing links cannot be stored in publication captions")
    return value


def link(label, url, *, channel=False):
    url = safe_url(url, channel=channel)
    return f'<a href="{escape(url, quote=True)}">{escape(str(label))}</a>' if url else ""


def render_caption(kind, context, config=None, *, limit=1024):
    config = {**DEFAULT_CONFIG, **(config or {})}
    labels = {**DEFAULT_CONFIG["labels"], **config.get("labels", {})}
    if kind == "album_intro":
        album_type = str(context.get("release_type", "LP")).upper()
        title = escape(str(context.get("title", "")))
        artists = " × ".join(escape(str(name)) for name in context.get("artists", []))
        lines = [f"<b>{title}</b>", f"{escape(album_type)} · {artists}"]
        features = context.get("features") or []
        if features:
            lines.append("feat. " + " · ".join(f"<i>{escape(str(name))}</i>" for name in features))
        bottom = []
        if context.get("original_album_post_url"):
            bottom.append(link(labels["original_album_post_url"], context["original_album_post_url"], channel=True))
        platforms = [link(labels[name], context[name]) for name in ("spotify_url", "soundcloud_url") if context.get(name)]
        if platforms:
            bottom.append(" / ".join(platforms))
        bottom_text = "\n".join(bottom)
        if bottom_text:
            bottom_text += "\n\n"
        bottom_text += escape(str(config["intro_footer"]))
        base = "\n".join(lines) + "\n\n" + bottom_text
        if visible_length(base) > limit:
            raise CaptionError("Core introduction exceeds caption limit; shorten the verified display/template values")
        included, overflow = [], []
        prior = context.get("previous_singles") or []
        heading = escape(str(config["prior_heading"]))
        for item in prior:
            row = "› " + link(item["title"], item["url"], channel=True)
            trial = "\n".join(lines) + "\n\n" + heading + "\n" + "\n".join([*included, row]) + "\n\n" + bottom_text
            if overflow or visible_length(trial) > limit:
                overflow.append(row)
            else:
                included.append(row)
        result = "\n".join(lines)
        if included:
            result += "\n\n" + heading + "\n" + "\n".join(included)
        result += "\n\n" + bottom_text
        chunks = []
        for row in overflow:
            if visible_length(row) > 4096:
                raise CaptionError("A prior-single link exceeds text-message limit")
            if not chunks or visible_length(chunks[-1] + "\n" + row) > 4096:
                chunks.append(row)
            else:
                chunks[-1] += "\n" + row
        return RenderedCaption(result, tuple(chunks))
    header = config["header"]
    if kind == "album_track_audio":
        header = config["ep_header"] if str(context.get("release_type", "")).lower() == "ep" else config["lp_header"]
    rows = []
    for key in config["rows"]:
        if key == "platforms":
            platform_rows = [link(labels[name], context[name]) for name in ("spotify_url", "soundcloud_url") if context.get(name)]
            if platform_rows:
                rows.append(" / ".join(platform_rows))
        elif key in labels and context.get(key):
            rows.append(link(labels[key], context[key], channel=key in {"album_post_url", "original_track_post_url"}))
    blocks = ([f"<b>{escape(str(header))}</b>"] if header else []) + (["\n".join(rows)] if rows else []) + [escape(str(config["footer"]))]
    result = "\n\n".join(blocks)
    if visible_length(result) > limit:
        raise CaptionError("Audio caption exceeds the supported caption limit")
    return RenderedCaption(result)
