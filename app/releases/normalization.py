import re
import unicodedata


_ZERO_WIDTH_AND_FORMAT = {"Cf", "Mn", "Me"}
_ARABIC_EQUIVALENTS = str.maketrans({
    "ي": "ی", "ى": "ی", "ئ": "ی", "ك": "ک", "ۀ": "ه", "ة": "ه",
    "أ": "ا", "إ": "ا", "آ": "ا",
})
_FEATURE_SEPARATOR = re.compile(r"\b(?:featuring|feat|ft|with)\b\.?", re.IGNORECASE)
_SLASH_FEATURE_SEPARATOR = re.compile(r"(?<!\w)w\s*/\s*", re.IGNORECASE)
_EDITION_MARKERS = {
    "remix": re.compile(r"\b(?:re\s*mix|remix)\b|ریمیکس", re.IGNORECASE),
    "live": re.compile(r"\blive\b|زنده", re.IGNORECASE),
    "instrumental": re.compile(r"\b(?:instrumental|inst)\b|اینسترومنتال|بی کلام", re.IGNORECASE),
    "deluxe": re.compile(r"\bdeluxe\b|دلوکس", re.IGNORECASE),
    "rerelease": re.compile(r"\b(?:re[\s-]*release|reissue|remaster(?:ed)?)\b|بازنشر", re.IGNORECASE),
}


def normalize_text(value):
    """Comparison-only Unicode normalization; callers retain the source value."""
    value = unicodedata.normalize("NFKC", str(value or "")).casefold().translate(_ARABIC_EQUIVALENTS)
    # Treat Persian half-space like a word boundary for matching, not as a
    # distinction from names typed with an ordinary space.
    value = value.replace("\u200c", " ")
    value = "".join(char for char in value if unicodedata.category(char) not in _ZERO_WIDTH_AND_FORMAT)
    value = _SLASH_FEATURE_SEPARATOR.sub(" feat ", value)
    value = _FEATURE_SEPARATOR.sub(" feat ", value)
    value = "".join(char if char.isalnum() else " " for char in value)
    return " ".join(value.split())


def edition_markers(value):
    normalized = unicodedata.normalize("NFKC", str(value or "")).casefold().translate(_ARABIC_EQUIVALENTS)
    return [kind for kind, pattern in _EDITION_MARKERS.items() if pattern.search(normalized)]


def base_title_for_edition(value, markers=None):
    base = unicodedata.normalize("NFKC", str(value or ""))
    for marker in markers if markers is not None else edition_markers(base):
        base = _EDITION_MARKERS[marker].sub(" ", base)
    return normalize_text(base)
