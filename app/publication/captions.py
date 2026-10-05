import re
from dataclasses import dataclass
from html import escape, unescape
from urllib.parse import parse_qsl, urlsplit


class CaptionError(ValueError):
    pass


DEFAULT_CONFIG = {
    "audio_layout": "linked_heading", "archive_header": "Fave",
    "brand_label": "Rap Farsi Drop", "brand_url": "https://t.me/RapFaDrop",
    "header": "Drop", "lp_header": "LP Drop", "ep_header": "EP Drop",
    "footer": "t.me/RapFaDrop", "intro_footer": "t.me/RapFaDrop",
    "prior_heading": "Previously released from this album:",
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


def confirmed_message_url(value, context):
    """Only the service's confirmed same-channel binding can select a message link."""
    url = safe_url(value, channel=True)
    parts = urlsplit(url)
    path = parts.path.strip("/").split("/")
    target = str(context.get("channel_target", "-1004311149640"))
    if target in {"-1004311149640", "@RapFaDrop"}:
        allowed = len(path) == 2 and path[0].lower() == "rapfadrop" or len(path) == 3 and path[:2] == ["c", "4311149640"]
    else:
        allowed = len(path) == 2 or len(path) == 3 and path[:2] == ["c", target.removeprefix("-100")]
    return url if allowed and path[-1].isdigit() and int(path[-1]) > 0 else ""


def compact_audio(kind, context, config, labels, limit):
    for key in ('spotify_url','soundcloud_url','album_post_url','original_track_post_url','original_album_post_url','music_video_url'):
        if context.get(key):safe_url(context[key],channel=key.endswith('post_url'))
    header = config["archive_header"] if kind == "archive_audio" else config["header"]
    if kind == "album_track_audio":
        header = config["ep_header"] if str(context.get("release_type", "")).lower() == "ep" else config["lp_header"]
    lines = [f"<b>{escape(str(header))}</b>"] if header else []
    version = context.get("version_type")
    if version in {"instrumental", "reissue", "deluxe"}:
        text = version.capitalize()
        original = confirmed_message_url(context.get("original_track_post_url") or context.get("original_album_post_url"), context) if context.get("original_confirmed") else ""
        if original:
            text += " (" + link(labels["original_track_post_url"], original, channel=True) + ")"
        lines.append(text)
    selected = ""
    if context.get("album_intro_confirmed") and context.get("album_post_url"):
        album = confirmed_message_url(context["album_post_url"], context)
        if album:
            selected = link(labels["album_post_url"], album, channel=True)
    if not selected:
        for key in ("spotify_url", "soundcloud_url"):
            if context.get(key):
                selected = link(labels[key], context[key])
                break
    brand = link(config["brand_label"], config["brand_url"], channel=True)
    lines.append(" · ".join(x for x in (selected, brand) if x))
    result = "\n".join(lines)
    if visible_length(result) > limit:
        raise CaptionError("Audio caption exceeds the supported caption limit")
    return RenderedCaption(result)


def linked_heading_audio(kind, context, config, labels, limit):
    for key in ('spotify_url', 'soundcloud_url', 'album_post_url', 'original_track_post_url', 'original_album_post_url'):
        if context.get(key):
            safe_url(context[key], channel=key.endswith('post_url'))
    header = config['archive_header'] if kind == 'archive_audio' else config['header']
    if kind == 'album_track_audio':
        header = config['ep_header'] if str(context.get('release_type', '')).lower() == 'ep' else config['lp_header']
    brand = safe_url(config['brand_url'], channel=True)
    lines = [f'<a href="{escape(brand, quote=True)}"><b>{escape(str(header))}</b></a>'] if header and brand else []
    version = context.get('version_type')
    if version in {'instrumental', 'reissue', 'deluxe'}:
        text = version.capitalize()
        original = confirmed_message_url(context.get('original_track_post_url') or context.get('original_album_post_url'), context) if context.get('original_confirmed') else ''
        if original:
            text += ' (' + link(labels['original_track_post_url'], original, channel=True) + ')'
        lines.append(text)
    links = [link(labels['spotify_url'], context['spotify_url'])] if context.get('spotify_url') else []
    album = confirmed_message_url(context['album_post_url'], context) if context.get('album_intro_confirmed') and context.get('album_post_url') else ''
    if album:
        links.append(link(labels['album_post_url'], album, channel=True))
    elif context.get('soundcloud_url'):
        links.append(link(labels['soundcloud_url'], context['soundcloud_url']))
    if links:
        lines.append('› ' + ' · '.join(links))
    result = '\n'.join(lines)
    if visible_length(result) > limit:
        raise CaptionError('Audio caption exceeds the supported caption limit')
    return RenderedCaption(result)


def render_caption(kind, context, config=None, *, limit=1024):
    # Unmigrated custom audio versions retain their historical rendering.
    raw_config=config or {}
    custom_legacy = False
    if config is not None and 'audio_layout' not in config:
        from operations.management.commands.refresh_owner_defaults import known_audio_default
        custom_legacy = not known_audio_default(config)
    config = {**DEFAULT_CONFIG, **(config or {})}
    if custom_legacy:
        config['audio_layout'] = 'legacy'
        config['archive_header'] = raw_config.get('archive_header', 'ARCHIVE')
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
    if config['audio_layout'] == 'linked_heading' and kind in {'archive_audio', 'single_audio', 'album_track_audio', 'edition'}:
        return linked_heading_audio(kind, context, config, labels, limit)
    if config["audio_layout"] == "compact" and kind in {'archive_audio','single_audio','album_track_audio','edition'}:
        return compact_audio(kind, context, config, labels, limit)
    header = config.get("archive_header", "ARCHIVE") if kind == "archive_audio" else config["header"]
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
    heading = [f"<b>{escape(str(header))}</b>"] if header else []
    blocks = (["\n".join(heading)] if heading else []) + (["\n".join(rows)] if rows else []) + [escape(str(config["footer"]))]
    result = "\n\n".join(blocks)
    if visible_length(result) > limit:
        raise CaptionError("Audio caption exceeds the supported caption limit")
    return RenderedCaption(result)
