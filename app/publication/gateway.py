import io
import json
import socket
import threading
import uuid
from dataclasses import dataclass
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener

from django.conf import settings
from PIL import Image


class GatewayError(RuntimeError):
    def __init__(self, message="Telegram rejected the operation", *, retry_after=60):
        self.retry_after = max(1, min(int(retry_after), 21600))
        super().__init__(message)


class UncertainGatewayError(GatewayError):
    pass


class TargetBlocked(GatewayError):
    pass


def normalize_target(target):
    value = str(target).strip()
    if not value or len(value) > 100:
        raise TargetBlocked("A target channel is required")
    return value.lower() if value.startswith("@") else value


def guard_target(target):
    target = normalize_target(target)
    cleaned = target.lower().replace("https://t.me/", "").replace("http://t.me/", "").lstrip("@")
    if cleaned == "rapfadrop" or (settings.TELEGRAM_PRODUCTION_CHAT_ID and target == str(settings.TELEGRAM_PRODUCTION_CHAT_ID)):
        raise TargetBlocked("Production-channel publication is blocked in M4")
    return target


@dataclass(frozen=True)
class GatewayResult:
    message_id: int
    chat_id: str
    message_url: str = ""


def message_url(chat_id, message_id, username=""):
    if username:
        return f"https://t.me/{username}/{message_id}"
    value = str(chat_id)
    return f"https://t.me/c/{value[4:]}/{message_id}" if value.startswith("-100") else ""


class FakeGateway:
    """Deterministic injectable gateway: never opens a network connection."""
    def __init__(self):
        self.calls = []
        self.failures = {}
        self.fail_audio_titles = {}
        self.counter = 100
        self.lock = threading.Lock()

    def execute(self, operation, target, payload):
        target = guard_target(target)
        with self.lock:
            self.calls.append({"operation": operation, "target": target, **payload})
            failures = self.failures.get(operation, [])
            if failures:
                raise failures.pop(0)
            title = payload.get("title")
            if operation == "send_audio" and self.fail_audio_titles.get(title, 0):
                self.fail_audio_titles[title] -= 1
                raise GatewayError("Fixture audio failure")
            if operation in {"edit_media", "edit_caption", "delete"}:
                mid = payload["message_id"]
            else:
                self.counter += 1
                mid = self.counter
            return GatewayResult(mid, target, message_url(target, mid, "rapfadrop_m4_fixture"))


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class TelegramGateway:
    """Bot-only HTTPS transport. Construction and every mutation require explicit opt-in."""
    def __init__(self):
        if not settings.TELEGRAM_LIVE_ENABLED or settings.TELEGRAM_MODE != "test" or not settings.TELEGRAM_BOT_TOKEN:
            raise TargetBlocked("Live test gateway requires enabled test mode and locally configured bot credentials")
        self._token = settings.TELEGRAM_BOT_TOKEN
        self._opener = build_opener(_NoRedirect())
        self._verified = threading.local()

    def _request(self, method, data, files=None):
        if method != "getChat":
            target = guard_target(data.get("chat_id", ""))
            if not settings.TELEGRAM_LIVE_ENABLED or settings.TELEGRAM_MODE != "test" or target != getattr(self._verified, "target", None):
                raise TargetBlocked("Gateway mutations require execute() with a freshly verified isolated target")
        if files:
            boundary = "rapfadrop" + uuid.uuid4().hex
            chunks = []
            for name, value in data.items():
                chunks.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode())
            for name, (filename, content, mime) in files.items():
                chunks.extend([f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"; filename="{filename}"\r\nContent-Type: {mime}\r\n\r\n'.encode(), content, b"\r\n"])
            chunks.append(f"--{boundary}--\r\n".encode())
            body = b"".join(chunks)
            content_type = f"multipart/form-data; boundary={boundary}"
        else:
            body = json.dumps(data).encode()
            content_type = "application/json"
        request = Request(f"https://api.telegram.org/bot{self._token}/{method}", data=body, headers={"Content-Type": content_type}, method="POST")
        try:
            with self._opener.open(request, timeout=settings.TELEGRAM_TIMEOUT_SECONDS) as response:
                raw = response.read(1024 * 1024)
        except HTTPError as exc:
            try:
                error = json.loads(exc.read(64 * 1024))
            except (ValueError, OSError):
                error = {}
            # A structured Bot API rejection proves no send. Unstructured 5xx is uncertain.
            if not isinstance(error, dict) or error.get("ok") is not False:
                raise UncertainGatewayError("Telegram HTTP response was not a structured rejection") from None
            code = int(error.get("error_code") or exc.code)
            retry = (error.get("parameters") or {}).get("retry_after", 60)
            if code >= 500:
                raise UncertainGatewayError("Telegram server error left the outcome uncertain") from None
            if method in {"editMessageCaption", "editMessageMedia"} and code == 400 and "message is not modified" in str(error.get("description", "")).lower():
                return True
            raise GatewayError(f"Telegram rejected operation (code {code})", retry_after=retry) from None
        except (URLError, OSError, socket.timeout):
            raise UncertainGatewayError("Telegram response was lost; reconciliation is required") from None
        try:
            result = json.loads(raw)
            if result.get("ok") is not True:
                raise GatewayError("Telegram returned a structured rejection")
            return result["result"]
        except (ValueError, KeyError, AttributeError):
            raise UncertainGatewayError("Telegram returned an unreadable success response") from None

    def _guard_live(self, target):
        target = guard_target(target)
        allowed = {normalize_target(value) for value in (settings.TELEGRAM_TEST_CHAT_ID, settings.TELEGRAM_REVIEW_CHAT_ID) if value}
        if target not in allowed:
            raise TargetBlocked("Target is not the locally configured test/review destination")
        try:
            chat = self._request("getChat", {"chat_id": target})
        except GatewayError:
            raise TargetBlocked("Test target could not be verified before mutation") from None
        if not isinstance(chat, dict) or "id" not in chat:
            raise TargetBlocked("Test target lookup was invalid")
        guard_target(chat["id"])
        if chat.get("username"):
            guard_target("@" + chat["username"])
        if settings.TELEGRAM_TEST_CHAT_ID and target == normalize_target(settings.TELEGRAM_TEST_CHAT_ID) and chat.get("type") != "channel":
            raise TargetBlocked("The configured test destination must resolve to an isolated channel")
        return str(chat["id"]), chat.get("username", "")

    def execute(self, operation, target, payload):
        chat_id, username = self._guard_live(target)
        methods = {"send_audio": self.send_audio, "send_intro": self.send_intro, "edit_media": self.edit_media, "edit_caption": self.edit_caption, "send_text": self.send_text, "reply": self.send_correction, "delete": self.delete_correction, "notify": self.notify_admin}
        if operation not in methods:
            raise GatewayError("Unsupported gateway operation")
        self._verified.target = chat_id
        try:
            result = methods[operation](chat_id, payload)
        finally:
            self._verified.target = None
        if isinstance(result, dict) and str((result.get("chat") or {}).get("id")) != chat_id:
            raise UncertainGatewayError("Telegram response did not confirm the configured target")
        mid = payload.get("message_id") if result is True else (result.get("message_id") if isinstance(result, dict) else None)
        if not mid:
            raise UncertainGatewayError("Telegram success did not contain a message ID")
        return GatewayResult(int(mid), chat_id, message_url(chat_id, int(mid), username))

    def _audio_files(self, payload):
        path = Path(payload["audio_path"])
        if path.suffix.lower() not in {".mp3", ".m4a"} or not path.is_file() or path.stat().st_size > 50_000_000:
            raise GatewayError("Bot API music-player audio requires MP3/M4A within 50 MB")
        files = {"audio": ("audio" + path.suffix.lower(), path.read_bytes(), "audio/mpeg" if path.suffix.lower() == ".mp3" else "audio/mp4")}
        if payload.get("artwork_path"):
            with Image.open(payload["artwork_path"]) as image:
                image = image.convert("RGB")
                image.thumbnail((320, 320))
                output = io.BytesIO()
                image.save(output, format="JPEG", quality=85)
                if len(output.getvalue()) < 200_000:
                    files["thumbnail"] = ("thumbnail.jpg", output.getvalue(), "image/jpeg")
        return files

    def send_audio(self, target, payload):
        data = {"chat_id": target, "caption": payload["caption_html"], "parse_mode": "HTML", "title": payload["title"], "performer": payload["performer"], "duration": payload.get("duration", 0)}
        return self._request("sendAudio", data, self._audio_files(payload))

    def send_intro(self, target, payload):
        path = Path(payload["artwork_path"])
        if not path.is_file() or path.stat().st_size > 10_000_000:
            raise GatewayError("A bounded official cover is required")
        with Image.open(path) as image:
            output = io.BytesIO()
            image.convert("RGB").save(output, format="JPEG", quality=90)
        return self._request("sendPhoto", {"chat_id": target, "caption": payload["caption_html"], "parse_mode": "HTML"}, {"photo": ("cover.jpg", output.getvalue(), "image/jpeg")})

    def edit_media(self, target, payload):
        files = self._audio_files(payload)
        media = {"type": "audio", "media": "attach://audio", "caption": payload["caption_html"], "parse_mode": "HTML", "title": payload["title"], "performer": payload["performer"]}
        if "thumbnail" in files:
            media["thumbnail"] = "attach://thumbnail"
        return self._request("editMessageMedia", {"chat_id": target, "message_id": payload["message_id"], "media": json.dumps(media)}, files)

    def edit_caption(self, target, payload):
        return self._request("editMessageCaption", {"chat_id": target, "message_id": payload["message_id"], "caption": payload["caption_html"], "parse_mode": "HTML"})

    def send_text(self, target, payload):
        return self._request("sendMessage", {"chat_id": target, "text": payload["caption_html"], "parse_mode": "HTML", "link_preview_options": {"is_disabled": True}})

    def send_correction(self, target, payload):
        return self._request("sendMessage", {"chat_id": target, "text": payload["caption_html"], "parse_mode": "HTML", "reply_parameters": {"message_id": payload["reply_to_message_id"]}})

    def delete_correction(self, target, payload):
        return self._request("deleteMessage", {"chat_id": target, "message_id": payload["message_id"]})

    def notify_admin(self, target, payload):
        return self.send_text(target, payload)
