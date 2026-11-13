from django.contrib.auth.signals import user_logged_in
from django.db.models import Q, QuerySet
from django.db.models.deletion import ProtectedError
from django.db.models.signals import post_delete, pre_delete
from django.dispatch import receiver

from .models import BaseCategory, BaseSubcategory, RecordDraft, User
from .taxonomy import (
    DEFAULT_CATEGORY_SLUG, TAXONOMY_MODELS, ensure_default_categories,
    get_default_category,
)


@receiver(user_logged_in)
def create_default_categories_on_sign_in(sender, user, request, **kwargs):
    ensure_default_categories(user)


# Post taxonomy FKs use DO_NOTHING so Django's deletion collector cannot collect
# posts as children of a deleted category/subcategory. Reassignments below run
# inside the collector's transaction before any taxonomy rows are removed.
TAXONOMY_DELETE_MODELS = {
    model: (record_type, models)
    for record_type, models in TAXONOMY_MODELS.items()
    for model in models[1:]
}


def _deletion_origin(origin, using):
    if isinstance(origin, QuerySet):
        # Freeze membership before pre_delete reassignments change conditions
        # used by a bulk deletion queryset (e.g. categories selected via posts).
        if not hasattr(origin, "_taxonomy_deleted_ids"):
            origin._taxonomy_deleted_ids = set(origin.using(using).values_list("pk", flat=True))
        return origin.model, origin._taxonomy_deleted_ids
    return type(origin), {getattr(origin, "pk", None)}


def _draft_values(data, key):
    value = data.get(key, [])
    return [str(item) for item in value] if isinstance(value, list) else ([str(value)] if value else [])


def preserve_posts_on_taxonomy_delete(sender, instance, using, origin=None, **kwargs):
    origin_model, origin_ids = _deletion_origin(origin, using)
    if origin_model is User:
        # An explicit account deletion still deletes that account's records.
        return
    record_type, (Record, Category, Subcategory, Tag) = TAXONOMY_DELETE_MODELS[sender]
    posts = Record.objects.using(using)
    destination = None
    if issubclass(sender, BaseCategory):
        if instance.slug == DEFAULT_CATEGORY_SLUG:
            replacement = getattr(origin, "_taxonomy_replacement_category", None)
            if (instance.user_id is not None or not isinstance(replacement, Category) or
                    replacement.pk == instance.pk or replacement.user_id is None or
                    replacement.slug != DEFAULT_CATEGORY_SLUG):
                raise ProtectedError("Uncategorized cannot be deleted.", [instance])
            # Legacy recovery explicitly merges an unowned duplicate into the
            # account's existing default, rather than removing its default.
            destination = replacement
        else:
            destination = get_default_category(Category, instance.user, using=using)
        posts.filter(category=instance).update(category=destination, subcategory=None)
    elif issubclass(sender, BaseSubcategory):
        parent_deleted = (
            origin_model is Subcategory and instance.parent_id in origin_ids
        ) or (
            origin_model is Category and instance.category_id in origin_ids
        )
        destination = instance.parent if instance.parent_id and not parent_deleted else None
        posts.filter(Q(subcategory=instance) | Q(subcategory__parent=instance)).update(subcategory=destination)
    # A tag only owns M2M links; deleting it never deletes or relocates a post.

    for draft in RecordDraft.objects.using(using).filter(user_id=instance.user_id, record_type=record_type):
        data = draft.data
        changed = False
        if sender is Category and str(instance.pk) in _draft_values(data, "category"):
            data["category"] = [str(destination.pk)]
            data["subcategory"] = [""]
            data["child_subcategory"] = [""]
            changed = True
        elif sender is Subcategory and (
            str(instance.pk) in _draft_values(data, "subcategory") or
            str(instance.pk) in _draft_values(data, "child_subcategory")
        ):
            data["subcategory"] = [str(destination.pk) if destination else ""]
            data["child_subcategory"] = [""]
            changed = True
        elif sender is Tag and str(instance.pk) in _draft_values(data, "tags"):
            data["tags"] = [value for value in _draft_values(data, "tags") if value != str(instance.pk)]
            changed = True
        if changed:
            draft.save(using=using, update_fields=["data"])


def clear_taxonomy_deletion_origin(sender, origin=None, **kwargs):
    if isinstance(origin, QuerySet) and hasattr(origin, "_taxonomy_deleted_ids"):
        del origin._taxonomy_deleted_ids


for model in TAXONOMY_DELETE_MODELS:
    pre_delete.connect(
        preserve_posts_on_taxonomy_delete, sender=model,
        dispatch_uid=f"core_preserve_posts_{model._meta.model_name}",
    )
    post_delete.connect(
        clear_taxonomy_deletion_origin, sender=model,
        dispatch_uid=f"core_clear_taxonomy_origin_{model._meta.model_name}",
    )
