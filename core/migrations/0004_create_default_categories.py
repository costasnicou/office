from django.db import migrations


CATEGORY_MODELS = (
    "ArticleCategory",
    "JournalCategory",
    "NoteCategory",
    "CentralPointCategory",
    "StrategyCategory",
    "DecisionCategory",
    "GoalCategory",
)


def create_default_categories(apps, schema_editor):
    User = apps.get_model("core", "User")
    users = User.objects.all().iterator()

    for user in users:
        for model_name in CATEGORY_MODELS:
            Category = apps.get_model("core", model_name)
            category = Category.objects.filter(
                user_id=user.pk,
                slug="uncategorized",
            ).first()
            if category is None:
                category = Category.objects.filter(
                    user_id=user.pk,
                    name__iexact="Uncategorized",
                ).first()
            if category is None:
                Category.objects.create(
                    user_id=user.pk,
                    name="Uncategorized",
                    slug="uncategorized",
                )
            elif category.name != "Uncategorized" or category.slug != "uncategorized":
                category.name = "Uncategorized"
                category.slug = "uncategorized"
                category.save(update_fields=["name", "slug"])


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0003_articlecategory_user_articlesubcategory_user_and_more"),
    ]

    operations = [
        migrations.RunPython(
            create_default_categories,
            migrations.RunPython.noop,
        ),
    ]
