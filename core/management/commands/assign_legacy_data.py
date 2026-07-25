from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from core.models import User
from core.taxonomy import TAXONOMY_MODELS


class Command(BaseCommand):
    help = (
        "Assign legacy records and taxonomy values with no owner to one user. "
        "Runs as a dry-run unless --apply is provided."
    )

    def add_arguments(self, parser):
        parser.add_argument("--username", required=True)
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Apply the ownership updates. Without this flag, no data changes.",
        )

    def handle(self, *args, **options):
        try:
            user = User.objects.get(username=options["username"])
        except User.DoesNotExist as error:
            raise CommandError("The requested user does not exist.") from error

        models = {
            model._meta.label_lower: model
            for group in TAXONOMY_MODELS.values()
            for model in group
        }
        counts = {
            label: model.objects.filter(user__isnull=True).count()
            for label, model in models.items()
        }

        collisions = []
        for label, model in models.items():
            unowned_slugs = model.objects.filter(
                user__isnull=True,
            ).exclude(slug="").values_list("slug", flat=True)
            conflicting_slugs = model.objects.filter(
                user=user,
                slug__in=unowned_slugs,
            ).values_list("slug", flat=True)
            for slug in conflicting_slugs:
                collisions.append(f"{label}: {slug}")

        total = sum(counts.values())
        self.stdout.write(
            f"Legacy unowned rows found: {total} for assignment to {user.username}"
        )
        for label, count in counts.items():
            if count:
                self.stdout.write(f"  {label}: {count}")

        if collisions:
            details = "\n  ".join(collisions)
            raise CommandError(
                "No changes were made because owned rows use the same slugs:\n"
                f"  {details}"
            )

        if not options["apply"]:
            self.stdout.write(
                self.style.WARNING(
                    "Dry run only. Re-run with --apply after checking these counts."
                )
            )
            return

        with transaction.atomic():
            for model in models.values():
                model.objects.filter(user__isnull=True).update(user=user)

        self.stdout.write(
            self.style.SUCCESS(
                f"Assigned {total} legacy rows to {user.username}."
            )
        )
