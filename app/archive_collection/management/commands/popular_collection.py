import json
import os
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from archive_collection.models import Collection
from archive_collection.services import freeze, run, status, link_confirmed_publications, refresh_published, retag_published
from archive_collection.gateway import CollectionGateway
from archive_collection.export import export


class Command(BaseCommand):
    help = "Explicit frozen archive only; no automatic scheduler."

    def add_arguments(self, parser):
        parser.add_argument("action", choices=("freeze", "status", "pause", "resume", "run", "export", "verify", "cleanup", "repair-links", "refresh-published", "retag-published"))
        parser.add_argument("--name", default="initial-popular-20261004")
        parser.add_argument("--sha", default="")
        parser.add_argument("--credentials", help="Protected JSON file containing token_file and expected_bot_id")
        parser.add_argument("--output", default="/tmp/popular-collection-report")
        parser.add_argument("--limit", type=int, default=166)

    def handle(self, *args, **options):
        action = options["action"]
        locked = action in {"freeze", "run", "repair-links", "refresh-published", "retag-published"}
        with connection.cursor() as cursor:
            if locked:
                cursor.execute("SELECT pg_try_advisory_lock(728319430)")
                if not cursor.fetchone()[0]:
                    raise CommandError("Another collection dispatcher is running")
        try:
            if action == "freeze":
                if len(options["sha"]) != 40:
                    raise CommandError("Freeze requires the exact tested application SHA")
                collection = freeze(options["name"], options["sha"])
            else:
                collection = Collection.objects.get(name=options["name"])
            if action in {"pause", "resume"}:
                collection.paused = action == "pause"
                collection.save(update_fields=("paused",))
            elif action in {"run", "verify", "refresh-published", "retag-published"}:
                if not options["credentials"]:
                    raise CommandError("Protected collection credentials file required")
                path = Path(options["credentials"])
                if path.stat().st_mode & 0o077:
                    raise CommandError("Collection credentials config must be private")
                config = json.loads(path.read_text())
                token_path = Path(config["token_file"])
                if token_path.stat().st_mode & 0o077:
                    raise CommandError("Collection token file must be private")
                gateway = CollectionGateway(collection, token_path.read_text().strip(), config["expected_bot_id"])
                if os.geteuid() == 0:
                    # Credentials stay root-only on disk; downloader and media work use app UID.
                    os.setgroups([])
                    os.setgid(1000)
                    os.setuid(1000)
                gateway._guard_live(collection.target)
                if action == "run":
                    run(collection, gateway, limit=max(1, min(options["limit"], 166)))
                elif action == "refresh-published":
                    self.stdout.write(json.dumps(refresh_published(collection, gateway)))
                elif action == "retag-published":
                    self.stdout.write(json.dumps(retag_published(collection, gateway)))
            elif action == "repair-links":
                self.stdout.write(json.dumps(link_confirmed_publications(collection)))
            if action == "export":
                export(collection, options["output"], processing_sha=options["sha"])
            if action == "cleanup":
                from archive_collection.services import cleanup_confirmed
                self.stdout.write(json.dumps(cleanup_confirmed(collection)))
            self.stdout.write(json.dumps(status(collection), ensure_ascii=False))
        except Collection.DoesNotExist:
            raise CommandError("Collection does not exist; freeze it after a verified recovery point") from None
        finally:
            if locked:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT pg_advisory_unlock(728319430)")
