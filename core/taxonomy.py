from .models import (
    Article, ArticleCategory, ArticleSubcategory, ArticleTag,
    CentralPoint, CentralPointCategory, CentralPointSubcategory, CentralPointTag,
    Decision, DecisionCategory, DecisionSubcategory, DecisionTag,
    Goal, GoalCategory, GoalSubcategory, GoalTag,
    Journal, JournalCategory, JournalSubcategory, JournalTag,
    Note, NoteCategory, NoteSubcategory, NoteTag,
    Strategy, StrategyCategory, StrategySubcategory, StrategyTag,
    BaseCategory,
)
from django.db.models import Case, IntegerField, Q, Value, When


DEFAULT_CATEGORY_NAME = "Uncategorized"
DEFAULT_CATEGORY_SLUG = "uncategorized"

TAXONOMY_MODELS = {
    "article": (Article, ArticleCategory, ArticleSubcategory, ArticleTag),
    "journal": (Journal, JournalCategory, JournalSubcategory, JournalTag),
    "note": (Note, NoteCategory, NoteSubcategory, NoteTag),
    "centralpoint": (
        CentralPoint, CentralPointCategory,
        CentralPointSubcategory, CentralPointTag,
    ),
    "strategy": (Strategy, StrategyCategory, StrategySubcategory, StrategyTag),
    "decision": (Decision, DecisionCategory, DecisionSubcategory, DecisionTag),
    "goal": (Goal, GoalCategory, GoalSubcategory, GoalTag),
}


def default_category_first(queryset):
    return queryset.annotate(
        _default_category_order=Case(
            When(slug=DEFAULT_CATEGORY_SLUG, then=Value(0)),
            default=Value(1),
            output_field=IntegerField(),
        )
    ).order_by("_default_category_order", "name")


def is_category_model(model):
    return issubclass(model, BaseCategory)


def get_default_category(category_model, user):
    category = category_model.objects.filter(
        Q(slug=DEFAULT_CATEGORY_SLUG) |
        Q(name__iexact=DEFAULT_CATEGORY_NAME),
        user=user,
    ).first()
    if category is None:
        category = category_model.objects.create(
            user=user,
            name=DEFAULT_CATEGORY_NAME,
            slug=DEFAULT_CATEGORY_SLUG,
        )
    elif (
        category.name != DEFAULT_CATEGORY_NAME or
        category.slug != DEFAULT_CATEGORY_SLUG
    ):
        category.name = DEFAULT_CATEGORY_NAME
        category.slug = DEFAULT_CATEGORY_SLUG
        category.save(update_fields=["name", "slug"])
    return category


def ensure_default_categories(user):
    if not user or not user.is_authenticated:
        return
    for _, category_model, _, _ in TAXONOMY_MODELS.values():
        get_default_category(category_model, user)
