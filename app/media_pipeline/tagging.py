import base64
import warnings
from pathlib import Path

from django.conf import settings
from PIL import Image

from mutagen import File as MutagenFile
from mutagen.flac import FLAC, Picture
from mutagen.id3 import APIC, COMM, ID3, TCOM, TDRC, TIT2, TIT3, TKEY, TALB, TENC, TPE1, TPE2, TPE3, TPUB, TRCK, TPOS, TCOP, WOAR
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4, MP4Cover
from mutagen.oggopus import OggOpus
from mutagen.oggvorbis import OggVorbis
from mutagen.wave import WAVE


SUPPORTED_ARTWORK_FORMATS = {"JPEG", "PNG"}
CHANNEL_FIELDS = {
    "subtitle", "comments", "album_artist_suffix", "album_suffix", "publisher",
    "encoded_by", "author_url", "copyright", "composers", "conductors", "initial_key",
}


class TaggingError(ValueError):
    pass


def validate_artwork(path):
    path = Path(path)
    if not path.is_file() or path.stat().st_size <= 0 or path.stat().st_size > settings.MEDIA_MAX_ARTWORK_BYTES:
        raise TaggingError("Artwork must be a non-empty image within the configured size limit")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(path) as image:
                if image.format not in SUPPORTED_ARTWORK_FORMATS:
                    raise TaggingError("Artwork must be JPEG or PNG")
                if image.width > 12000 or image.height > 12000:
                    raise TaggingError("Artwork dimensions exceed the configured safety limit")
                image.verify()
                return {"format": image.format, "mime_type": Image.MIME[image.format], "width": image.width, "height": image.height, "size_bytes": path.stat().st_size}
    except (OSError, Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        raise TaggingError("Artwork image failed validation") from exc


def prepare_tagged_copy(source_path, prepared_path, metadata, artwork_path=None):
    source_path = Path(source_path)
    prepared_path = Path(prepared_path)
    prepared_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    prepared_path.write_bytes(source_path.read_bytes())
    prepared_path.chmod(0o600)
    title = str(metadata.get("title") or "").strip()
    artists = [str(value).strip() for value in metadata.get("artists", []) if str(value).strip()]
    if not title or not artists:
        raise TaggingError("Official title and at least one credited artist are required")
    album = str(metadata.get("album") or title).strip()
    channel = settings.MEDIA_CHANNEL_TAG
    try:
        from operations.services import active_media_tag_fields
        tag_fields = active_media_tag_fields(settings.MEDIA_CHANNEL_TAG_FIELDS)
    except Exception:
        tag_fields = settings.MEDIA_CHANNEL_TAG_FIELDS
    configured = set(tag_fields) & CHANNEL_FIELDS
    album_with_tag = f"{album} | {channel}" if album and "album_suffix" in configured else album
    album_artist_with_tag = f"{artists[0]} | {channel}" if "album_artist_suffix" in configured else artists[0]
    unsupported = []
    mapped = sorted(configured & {"album_suffix", "album_artist_suffix"})
    art_info = validate_artwork(artwork_path) if artwork_path else None
    image_data = Path(artwork_path).read_bytes() if artwork_path else None
    image_mime = art_info["mime_type"] if art_info else ""
    audio = MutagenFile(prepared_path)
    if audio is None:
        raise TaggingError("Mutagen does not support metadata for this audio container")
    if isinstance(audio, (MP3, WAVE)):
        tags = audio.tags
        if tags is None:
            audio.add_tags()
            tags = audio.tags
        tags["TIT2"] = TIT2(encoding=3, text=title)
        tags["TPE1"] = TPE1(encoding=3, text=artists)
        tags["TALB"] = TALB(encoding=3, text=album_with_tag)
        tags["TPE2"] = TPE2(encoding=3, text=album_artist_with_tag)
        _set_id3(tags, configured, mapped, unsupported)
        if metadata.get("release_date"):
            tags["TDRC"] = TDRC(encoding=3, text=str(metadata["release_date"]))
        if metadata.get("track_number"):
            tags["TRCK"] = TRCK(encoding=3, text=str(metadata["track_number"]))
        if metadata.get("disc_number"):
            tags["TPOS"] = TPOS(encoding=3, text=str(metadata["disc_number"]))
        if art_info:
            tags.delall("APIC")
            tags.add(APIC(encoding=3, mime=image_mime, type=3, desc="Cover", data=image_data))
        audio.save()
    elif isinstance(audio, MP4):
        tags = audio.tags
        if tags is None:
            audio.add_tags()
            tags = audio.tags
        tags["\xa9nam"] = [title]
        tags["\xa9ART"] = artists
        tags["\xa9alb"] = [album_with_tag]
        tags["aART"] = [album_artist_with_tag]
        mp4_fields = {
            "comments": ("\xa9cmt", [channel]), "subtitle": ("desc", [channel]),
            "encoded_by": ("\xa9too", [channel]), "copyright": ("cprt", [channel]),
            "composers": ("\xa9wrt", [channel]),
        }
        for field, (key, value) in mp4_fields.items():
            if field in configured:
                tags[key] = value
                mapped.append(field)
            else:
                tags.pop(key, None)
        tags["\xa9day"] = [str(metadata["release_date"])] if metadata.get("release_date") else []
        tags["trkn"] = [(int(metadata["track_number"]), 0)] if metadata.get("track_number") else []
        tags["disk"] = [(int(metadata["disc_number"]), 0)] if metadata.get("disc_number") else []
        if art_info:
            image_format = MP4Cover.FORMAT_JPEG if art_info["format"] == "JPEG" else MP4Cover.FORMAT_PNG
            tags["covr"] = [MP4Cover(image_data, imageformat=image_format)]
        unsupported.extend(sorted(configured & {"publisher", "author_url", "conductors", "initial_key"}))
        audio.save()
    elif isinstance(audio, FLAC):
        mapped.extend(_write_vorbis_tags(audio, metadata, artists, album_with_tag, album_artist_with_tag, channel, configured))
        if art_info:
            picture = Picture()
            picture.type = 3
            picture.mime = image_mime
            picture.desc = "Cover"
            picture.data = image_data
            audio.clear_pictures()
            audio.add_picture(picture)
        audio.save()
    elif isinstance(audio, (OggVorbis, OggOpus)):
        mapped.extend(_write_vorbis_tags(audio, metadata, artists, album_with_tag, album_artist_with_tag, channel, configured))
        if art_info:
            picture = Picture()
            picture.type = 3
            picture.mime = image_mime
            picture.desc = "Cover"
            picture.data = image_data
            audio["metadata_block_picture"] = [base64.b64encode(picture.write()).decode("ascii")]
        audio.save()
    else:
        raise TaggingError(f"Unsupported Mutagen tagging class: {type(audio).__name__}")

    return {
        "format": type(audio).__name__,
        "channel_tag": channel,
        "mapped_fields": ["title", "main_artist", "album", "track_number", "disc_number", "release_date", *sorted(mapped)],
        "unsupported_fields": unsupported,
        "artwork": {"state": "embedded", **art_info} if art_info else {"state": "not_provided"},
        "readback": readback_tags(prepared_path, title, artists, album, channel, bool(art_info), configured),
    }


def _set_id3(tags, configured, mapped, unsupported):
    frames = {
        "subtitle": ("TIT3", TIT3(encoding=3, text=settings.MEDIA_CHANNEL_TAG)),
        "comments": ("COMM", COMM(encoding=3, lang="eng", desc="", text=settings.MEDIA_CHANNEL_TAG)),
        "publisher": ("TPUB", TPUB(encoding=3, text=settings.MEDIA_CHANNEL_TAG)),
        "encoded_by": ("TENC", TENC(encoding=3, text=settings.MEDIA_CHANNEL_TAG)),
        "author_url": ("WOAR", WOAR(url=settings.MEDIA_AUTHOR_URL)),
        "copyright": ("TCOP", TCOP(encoding=3, text=settings.MEDIA_CHANNEL_TAG)),
        "composers": ("TCOM", TCOM(encoding=3, text=settings.MEDIA_CHANNEL_TAG)),
        "conductors": ("TPE3", TPE3(encoding=3, text=settings.MEDIA_CHANNEL_TAG)),
        "initial_key": ("TKEY", TKEY(encoding=3, text=settings.MEDIA_CHANNEL_TAG)),
    }
    for name, (frame_id, frame) in frames.items():
        if name in configured:
            tags[frame_id] = frame
            mapped.append(name)
        else:
            tags.delall(frame_id)


def _write_vorbis_tags(audio, metadata, artists, album, album_artist, channel, configured):
    if audio.tags is None:
        audio.add_tags()
    fields = {
        "TITLE": [str(metadata["title"])],
        "ARTIST": artists,
        "ALBUM": [album],
        "ALBUMARTIST": [album_artist],
    }
    fields_by_name = {
        "subtitle": "SUBTITLE", "comments": "COMMENT", "publisher": "PUBLISHER",
        "encoded_by": "ENCODED-BY", "copyright": "COPYRIGHT", "composers": "COMPOSER",
        "conductors": "CONDUCTOR", "initial_key": "INITIALKEY",
    }
    mapped = []
    for name, key in fields_by_name.items():
        if name in configured:
            fields[key] = [channel]
            mapped.append(name)
        else:
            audio.pop(key, None)
    if "author_url" in configured:
        fields["URL"] = [settings.MEDIA_AUTHOR_URL]
        mapped.append("author_url")
    else:
        audio.pop("URL", None)
    if metadata.get("release_date"):
        fields["DATE"] = [str(metadata["release_date"])]
    if metadata.get("track_number"):
        fields["TRACKNUMBER"] = [str(metadata["track_number"])]
    if metadata.get("disc_number"):
        fields["DISCNUMBER"] = [str(metadata["disc_number"])]
    for key, value in fields.items():
        audio[key] = value
    return mapped


def readback_tags(path, expected_title, expected_artists, expected_album, channel, expect_artwork, configured=None):
    configured = set(configured if configured is not None else settings.MEDIA_CHANNEL_TAG_FIELDS)
    # Accept the historical helper form where callers pass the expected tagged album.
    if "album_suffix" in configured and expected_album.endswith(f" | {channel}"):
        expected_album = expected_album[: -(len(channel) + 3)]
    audio = MutagenFile(path)
    if audio is None or audio.tags is None:
        raise TaggingError("Prepared metadata could not be read back")
    tags = audio.tags
    if isinstance(tags, ID3):
        title = str(tags.get("TIT2", ""))
        artists = list(tags.get("TPE1", []))
        album = str(tags.get("TALB", ""))
        channel_present = _channel_readback(tags, channel, configured, id3=True)
        has_art = any(frame.FrameID == "APIC" for frame in tags.values())
    elif isinstance(audio, MP4):
        title = _first(tags.get("\xa9nam"))
        artists = tags.get("\xa9ART", [])
        album = _first(tags.get("\xa9alb"))
        channel_present = _channel_readback(tags, channel, configured, mp4=True)
        has_art = bool(tags.get("covr"))
    else:
        title = _first(tags.get("title") or tags.get("TITLE"))
        artists = tags.get("artist") or tags.get("ARTIST") or []
        album = _first(tags.get("album") or tags.get("ALBUM"))
        channel_present = _channel_readback(tags, channel, configured)
        has_art = bool(getattr(audio, "pictures", [])) or bool(tags.get("metadata_block_picture"))
    artists = [str(value) for value in artists]
    result = {
        "title_matches": title == expected_title,
        "main_artists_match": artists == expected_artists,
        "album_suffix_matches": album == (f"{expected_album} | {channel}" if "album_suffix" in configured and expected_album else expected_album),
        "channel_fields_read_back": channel_present,
        "artwork_read_back": has_art if expect_artwork else None,
    }
    if not all(result[key] for key in ("title_matches", "main_artists_match", "album_suffix_matches", "channel_fields_read_back")):
        raise TaggingError(f"Prepared core metadata did not match its required readback: {result}")
    if expect_artwork and not has_art:
        raise TaggingError("Embedded artwork did not survive format-aware readback")
    return result


def _channel_readback(tags, channel, configured, id3=False, mp4=False):
    keys = {
        "subtitle": "TIT3" if id3 else "desc" if mp4 else "subtitle",
        "comments": "COMM" if id3 else "\xa9cmt" if mp4 else "comment",
        "publisher": "TPUB" if id3 else "PUBLISHER",
        "encoded_by": "TENC" if id3 else "\xa9too" if mp4 else "ENCODED-BY",
        "author_url": "WOAR" if id3 else "URL",
        "copyright": "TCOP" if id3 else "cprt" if mp4 else "COPYRIGHT",
        "composers": "TCOM" if id3 else "\xa9wrt" if mp4 else "COMPOSER",
        "conductors": "TPE3" if id3 else "CONDUCTOR",
        "initial_key": "TKEY" if id3 else "INITIALKEY",
    }
    for field in configured & keys.keys():
        raw = tags.getall(keys[field]) if id3 and field == "comments" else tags.get(keys[field])
        value = _tag_text(raw)
        if value and (channel in value or (field == "author_url" and settings.MEDIA_AUTHOR_URL in value)):
            return True
    album_artist = str(tags.get("TPE2" if id3 else "aART" if mp4 else "albumartist", ""))
    return "album_artist_suffix" in configured and channel in album_artist


def _tag_text(value):
    if value is None:
        return ""
    if hasattr(value, "text"):
        return " ".join(str(item) for item in value.text)
    if hasattr(value, "url"):
        return str(value.url)
    if isinstance(value, (list, tuple)):
        return " ".join(_tag_text(item) for item in value)
    return str(value)


def _first(values):
    if not values:
        return ""
    if isinstance(values, str):
        return values
    return str(values[0])
