import getpass
import os

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError

from operations.services import configure_operator_group


class Command(BaseCommand):
    help = "Create a separately named RapFaDrop operator account. Password resets are performed from the audited panel."

    def add_arguments(self, parser):
        parser.add_argument("username")
        parser.add_argument("--email", default="")

    def handle(self, *args, **options):
        User = get_user_model()
        username = options["username"]
        try:
            user = User.objects.get(username=username)
            raise CommandError("That username already exists; password resets must use the audited operator panel.")
        except User.DoesNotExist:
            user = User(username=username, email=options["email"], is_staff=True, is_superuser=False)

        password = os.environ.get("RAPFADROP_ADMIN_PASSWORD") or getpass.getpass("Administrator password: ")
        confirm = getpass.getpass("Confirm password: ") if not os.environ.get("RAPFADROP_ADMIN_PASSWORD") else password
        if not password or password != confirm:
            raise CommandError("Password is empty or confirmation did not match.")
        try:
            validate_password(password, user)
        except ValidationError as exc:
            raise CommandError("Password does not meet the configured password policy.") from exc
        user.set_password(password)
        user.is_staff = True
        user.is_superuser = False
        if options["email"]:
            user.email = options["email"]
        user.save()
        user.groups.add(configure_operator_group())
        self.stdout.write(self.style.SUCCESS(f"Operator account {username!r} is ready; credentials were not displayed or logged."))
