"""Explicit collection capability, unavailable to ordinary workers and scheduler tasks."""
import threading
import hashlib
from pathlib import Path
from urllib.request import build_opener

from publication.gateway import TelegramGateway, TargetBlocked, _NoRedirect
from .models import Collection

TARGET = "-1004311149640"


class CollectionGateway(TelegramGateway):
    def __init__(self, collection, token, expected_bot_id):
        self.collection_id = collection.pk
        self._token = token
        self.expected_bot_id = int(expected_bot_id)
        if not token or collection.target != TARGET or not collection.frozen_at:
            raise TargetBlocked("Frozen authorized collection and protected bot credential required")
        self._opener = build_opener(_NoRedirect())
        self._verified = threading.local()

    def _check_request(self, method, data):
        if method in {"getMe", "getChat", "getChatMember"}:
            if method != "getMe" and str(data.get("chat_id")) != TARGET:
                raise TargetBlocked("Collection read target mismatch")
            return
        from .services import assert_collection_safe
        assert_collection_safe(Collection.objects.get(pk=self.collection_id))
        if method != "sendAudio" or str(data.get("chat_id")) != TARGET or getattr(self._verified, "target", None) != TARGET:
            raise TargetBlocked("Collection capability permits only verified frozen audio sends")

    def _guard_live(self, target):
        from .services import assert_collection_safe
        collection = Collection.objects.get(pk=self.collection_id)
        assert_collection_safe(collection)
        if str(target) != TARGET:
            raise TargetBlocked("Owner-approved collection target mismatch")
        bot = self._request("getMe", {})
        chat = self._request("getChat", {"chat_id": TARGET})
        member = self._request("getChatMember", {"chat_id": TARGET, "user_id": self.expected_bot_id})
        if (not isinstance(bot, dict) or bot.get("id") != self.expected_bot_id or bot.get("is_bot") is not True or
                str(chat.get("id")) != TARGET or chat.get("type") != "channel" or
                str(chat.get("username", "")).lower() != "rapfadrop" or
                member.get("status") not in {"administrator", "creator"} or
                (member.get("status") != "creator" and member.get("can_post_messages") is not True)):
            raise TargetBlocked("Bot identity, exact production channel or posting permission mismatch")
        evidence = {"bot_id": bot["id"], "bot_username": bot.get("username"), "chat_id": chat["id"],
                    "chat_username": chat.get("username"), "chat_title": chat.get("title"),
                    "member_status": member["status"], "can_post_messages": member.get("can_post_messages")}
        Collection.objects.filter(pk=collection.pk).update(verification=evidence)
        return TARGET, chat["username"]

    def execute(self, operation, target, payload):
        from publication.models import PublicationAttempt
        from .services import authorize_publication
        attempt = PublicationAttempt.objects.filter(state="pending", payload=payload,
            publication__archive_recordings__collection_id=self.collection_id).select_related("publication__channel").first()
        if attempt is None:
            raise TargetBlocked("No collection-owned pending publication attempt")
        authorize_publication(self.collection_id, attempt.publication, operation, payload)
        return super().execute(operation, target, payload)

    def readback(self, recording):
        pub = recording.publication
        if not pub or not pub.message_id or pub.channel.target != TARGET:
            raise TargetBlocked("Readback requires a confirmed collection production message")
        attempt = pub.attempts.filter(state="succeeded", operation="send_audio").order_by("-pk").first()
        media = (attempt.response.get("media") or {}) if attempt else {}
        if not media.get("file_id") or media.get("file_size", 0) > 20_000_000:
            return {"status": "blocked", "reason": "No durable file_id or file exceeds hosted Bot API 20MB readback limit"}
        from urllib.request import Request
        info = self._transport_request("getFile", {"file_id": media["file_id"]})
        relative = str(info.get("file_path") or "")
        if not relative or ".." in relative or relative.startswith("/") or "?" in relative:
            raise TargetBlocked("Invalid Telegram readback path")
        # Credential-bearing URL exists only in transport memory and is never recorded.
        digest = hashlib.sha256()
        size = 0
        try:
            with self._opener.open(Request(f"https://api.telegram.org/file/bot{self._token}/{relative}"), timeout=60) as response:
                while chunk := response.read(65536):
                    size += len(chunk)
                    if size > 20_000_000:
                        raise TargetBlocked("Readback exceeded bounded file size")
                    digest.update(chunk)
        except TargetBlocked:
            raise
        except Exception:
            return {"status": "blocked", "reason": "Telegram file readback unavailable; confirmed send remains durable"}
        prepared = Path(pub.candidate.prepared_path)
        if not prepared.is_file():
            return {"status": "blocked", "reason": "Prepared copy no longer retained for byte comparison"}
        expected = hashlib.sha256(prepared.read_bytes()).hexdigest()
        return {"status": "passed" if digest.hexdigest() == expected else "mismatch",
                "bytes": size, "sha256": digest.hexdigest(), "prepared_sha256": expected}
