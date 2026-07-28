from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0004_create_default_categories"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="RecordDraft",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("record_type", models.CharField(max_length=32)),
                ("record_key", models.CharField(default="__new__", max_length=255)),
                ("data", models.JSONField(default=dict)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="record_drafts", to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddConstraint(
            model_name="recorddraft",
            constraint=models.UniqueConstraint(fields=("user", "record_type", "record_key"), name="unique_user_record_draft"),
        ),
    ]
