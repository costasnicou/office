from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from core.models import User
from core.taxonomy import DEFAULT_CATEGORY_SLUG, TAXONOMY_MODELS


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
        category_models = {
            category_model
            for _, category_model, _, _ in TAXONOMY_MODELS.values()
        }

        collisions = []
        default_merges = []
        for label, model in models.items():
            unowned_slugs = model.objects.filter(
                user__isnull=True,
            ).exclude(slug="").values_list("slug", flat=True)
            conflicting_slugs = model.objects.filter(
                user=user,
                slug__in=unowned_slugs,
            ).values_list("slug", flat=True)
            for slug in conflicting_slugs:
                if model in category_models and slug == DEFAULT_CATEGORY_SLUG:
                    default_merges.append(label)
                else:
                    collisions.append(f"{label}: {slug}")

        for (
            record_model, category_model, subcategory_model, _
        ) in TAXONOMY_MODELS.values():
            legacy_defaults = category_model.objects.filter(
                user__isnull=True,
                slug=DEFAULT_CATEGORY_SLUG,
            )
            if not legacy_defaults.exists():
                continue
            if record_model.objects.filter(
                category__in=legacy_defaults,
            ).exclude(user__isnull=True).exists():
                collisions.append(
                    f"{category_model._meta.label_lower}: "
                    "owned records reference the legacy default"
                )
            if subcategory_model.objects.filter(
                category__in=legacy_defaults,
            ).exclude(user__isnull=True).exists():
                collisions.append(
                    f"{category_model._meta.label_lower}: "
                    "owned subcategories reference the legacy default"
                )

        total = sum(counts.values())
        self.stdout.write(
            f"Legacy unowned rows found: {total} for assignment to {user.username}"
        )
        for label, count in counts.items():
            if count:
                self.stdout.write(f"  {label}: {count}")
        if default_merges:
            self.stdout.write(
                "Legacy Uncategorized categories to merge safely:"
            )
            for label in default_merges:
                self.stdout.write(f"  {label}")

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
            for (
                record_model, category_model, _, _
            ) in TAXONOMY_MODELS.values():
                legacy_defaults = category_model.objects.filter(
                    user__isnull=True,
                    slug=DEFAULT_CATEGORY_SLUG,
                )
                owned_default = category_model.objects.filter(
                    user=user,
                    slug=DEFAULT_CATEGORY_SLUG,
                ).first()
                if owned_default is None or not legacy_defaults.exists():
                    continue

                record_model.objects.filter(
                    user__isnull=True,
                    category__in=legacy_defaults,
                ).update(
                    category=owned_default,
                    subcategory=None,
                )
                legacy_defaults.delete()

            for model in models.values():
                model.objects.filter(user__isnull=True).update(user=user)

        self.stdout.write(
            self.style.SUCCESS(
                f"Recovered {total} legacy rows for {user.username}."
            )
        )
