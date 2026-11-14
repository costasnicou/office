from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.db import transaction

from .models import (
    Article, ArticleCategory, ArticleSubcategory, ArticleTag,
    CentralPoint, CentralPointCategory, CentralPointSubcategory, CentralPointTag,
    Decision, DecisionCategory, DecisionSubcategory, DecisionTag,
    Goal, GoalCategory, GoalSubcategory, GoalTag,
    Journal, JournalCategory, JournalSubcategory, JournalTag,
    Note, NoteCategory, NoteSubcategory, NoteTag,
    Strategy, StrategyCategory, StrategySubcategory, StrategyTag,
    User,
)
from .taxonomy import (
    DEFAULT_CATEGORY_NAME, DEFAULT_CATEGORY_SLUG, default_category_first,
)


class RegistrationForm(UserCreationForm):
    """Create a local account with a unique, normalized email address."""

    first_name = forms.CharField(label="Name", max_length=150)
    last_name = forms.CharField(label="Surname", max_length=150)
    email = forms.EmailField(label="Email")

    class Meta(UserCreationForm.Meta):
        model = User
        fields = (
            "first_name", "last_name", "username", "email",
            "password1", "password2",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        placeholders = {
            "first_name": "Name",
            "last_name": "Surname",
            "username": "Username",
            "email": "you@example.com",
            "password1": "Password",
            "password2": "Confirm password",
        }
        autocomplete = {
            "first_name": "given-name",
            "last_name": "family-name",
            "username": "username",
            "email": "email",
            "password1": "new-password",
            "password2": "new-password",
        }
        for name, field in self.fields.items():
            field.widget.attrs.update({
                "class": "auth-input",
                "placeholder": placeholders[name],
                "autocomplete": autocomplete[name],
            })

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email


class ScopedSubcategorySelect(forms.Select):
    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex, attrs)
        if hasattr(value, "instance"):
            option["attrs"]["data-category"] = value.instance.category_id
            option["attrs"]["data-parent"] = value.instance.parent_id or ""
        return option


class ScopedTagCheckboxes(forms.CheckboxSelectMultiple):
    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex, attrs)
        if hasattr(value, "instance"):
            option["attrs"]["data-category"] = value.instance.category_id
            option["attrs"]["data-subcategory"] = value.instance.subcategory_id or ""
            option["attrs"]["data-tag-name"] = value.instance.name
            scope = str(value.instance.subcategory) if value.instance.subcategory_id else value.instance.category.name
            option["label"] = f"{scope}: {value.instance.name}"
        return option


class TaxonomyModelForm(forms.ModelForm):
    """Model form that can create taxonomy values along with the record."""

    new_category = forms.CharField(
        label="New category",
        required=False,
        max_length=255,
        help_text="Enter a name only when the category is not in the list.",
    )
    new_subcategory = forms.CharField(
        label="New subcategory",
        required=False,
        max_length=255,
        help_text="Enter a name only when the subcategory is not in the list.",
    )
    new_child_subcategory = forms.CharField(
        label="New second-level subcategory", required=False, max_length=255,
        help_text="Create under the selected or newly entered first-level subcategory.",
    )
    new_tags = forms.CharField(
        label="New tags",
        required=False,
        help_text="Comma-separated tag names to create and attach.",
    )

    new_category_tags = forms.CharField(
        label="Create category tags", required=False,
        help_text="Separate names with commas. These tags will be selected for this post when you save.",
    )
    new_subcategory_tags = forms.CharField(
        label="Create tags for this subcategory", required=False,
        help_text="Separate names with commas. These tags will be selected for this post when you save.",
    )
    new_child_tags = forms.CharField(
        label="Create tags for this subcategory", required=False,
        help_text="Separate names with commas. These tags will be selected for this post when you save.",
    )

    category_model = None
    subcategory_model = None
    tag_model = None

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        self.fields["child_subcategory"] = forms.ModelChoiceField(
            label="Second-level subcategory", required=False,
            queryset=self.subcategory_model.objects.select_related("category", "parent").filter(
                user=self.user, parent__isnull=False,
            ).order_by("category__name", "parent__name", "name"),
            widget=ScopedSubcategorySelect(),
            empty_label="Select a second-level subcategory (optional)",
        )
        initial_subcategory = self.initial.get("subcategory")
        if initial_subcategory and not self.is_bound:
            selected = self.subcategory_model.objects.filter(user=self.user, pk=initial_subcategory).first()
            if selected and selected.parent_id:
                self.initial["subcategory"] = selected.parent_id
                self.initial["child_subcategory"] = selected.pk
        # Show pending names from older drafts in their most specific tag section.
        if not self.is_bound and self.initial.get("new_tags"):
            if self.initial.get("child_subcategory") or self.initial.get("new_child_subcategory"):
                tag_field = "new_child_tags"
            elif self.initial.get("subcategory") or self.initial.get("new_subcategory"):
                tag_field = "new_subcategory_tags"
            else:
                tag_field = "new_category_tags"
            self.initial[tag_field] = ", ".join(filter(None, [
                self.initial.get(tag_field, ""), self.initial["new_tags"],
            ]))
            self.initial["new_tags"] = ""
        order = []
        for name in self.fields:
            if name in {"child_subcategory", "new_child_subcategory"}:
                continue
            order.append(name)
            if name == "subcategory":
                order.append("child_subcategory")
            if name == "new_subcategory":
                order.append("new_child_subcategory")
        tag_fields = {"tags", "new_tags", "new_category_tags", "new_subcategory_tags", "new_child_tags"}
        self.order_fields([name for name in order if name not in tag_fields] +
                         ["tags", "new_category_tags", "new_subcategory_tags", "new_child_tags", "new_tags"])
        self.fields["category"].required = False
        self.fields["category"].queryset = default_category_first(
            self.category_model.objects.filter(user=self.user)
        )
        self.fields["category"].empty_label = "Select an existing category"
        self.fields["subcategory"].queryset = self.subcategory_model.objects.select_related(
            "category"
        ).filter(user=self.user, parent__isnull=True).order_by("category__name", "name")
        self.fields["subcategory"].widget = ScopedSubcategorySelect()
        self.fields["subcategory"].widget.choices = self.fields["subcategory"].choices
        self.fields["subcategory"].empty_label = "Select an existing subcategory (optional)"
        self.fields["tags"].queryset = self.tag_model.objects.filter(
            user=self.user
        ).select_related("category", "subcategory__parent").order_by("name")
        self.fields["tags"].widget = ScopedTagCheckboxes(
            attrs={"class": "tag-choice-input"}
        )
        self.fields["tags"].widget.choices = self.fields["tags"].choices
        self.fields["tags"].help_text = (
            "Select tags independently from the category and either subcategory level. Only selected tags belong to this post. Create new tags in the section for their category level."
        )

        placeholders = {
            "category": "Select an existing category",
            "subcategory": "Select an existing subcategory (optional)",
            "tags": "Select existing tags",
            "new_category": "Or enter a new category",
            "new_subcategory": "Or enter a new subcategory",
            "new_category_tags": "e.g. time management, habits",
            "new_subcategory_tags": "e.g. time&space",
            "new_child_tags": "e.g. space",
            "new_tags": "Or enter new tags separated by commas",
        }
        for field_name, field in self.fields.items():
            placeholder = placeholders.get(field_name, field.label)
            field.widget.attrs.update({
                "aria-label": field.label,
                "title": field.label,
                "placeholder": placeholder,
            })

    def clean(self):
        cleaned_data = super().clean()
        category = cleaned_data.get("category")
        subcategory = cleaned_data.get("subcategory")
        child = cleaned_data.get("child_subcategory")
        new_child = cleaned_data.get("new_child_subcategory", "").strip()
        new_category = cleaned_data.get("new_category", "").strip()
        new_subcategory = cleaned_data.get("new_subcategory", "").strip()

        if category and new_category:
            self.add_error("new_category", "Select a category or create one, not both.")
        if not category and not new_category:
            self.add_error("category", "Select a category or enter a new category name.")
        if subcategory and new_subcategory:
            self.add_error("new_subcategory", "Select a subcategory or create one, not both.")
        if subcategory and category and subcategory.category_id != category.pk:
            self.add_error("subcategory", "The subcategory must belong to the selected category.")
        if subcategory and new_category:
            self.add_error(
                "subcategory",
                "An existing subcategory cannot be used with a new category.",
            )
        is_default_category = (
            category and category.slug == DEFAULT_CATEGORY_SLUG
        ) or new_category.casefold() == DEFAULT_CATEGORY_NAME.casefold()
        if is_default_category and (subcategory or new_subcategory):
            self.add_error(
                "subcategory",
                "Uncategorized cannot have subcategories.",
            )
        if child and (not subcategory or child.parent_id != subcategory.pk or
                      child.category_id != getattr(category, "pk", None) or new_subcategory):
            self.add_error("child_subcategory", "Choose a child of the selected first-level subcategory.")
        if child and new_child:
            self.add_error("new_child_subcategory", "Select a second-level subcategory or create one, not both.")
        if new_child and not (subcategory or new_subcategory):
            self.add_error("new_child_subcategory", "Choose or create a first-level subcategory first.")
        if is_default_category and (child or new_child):
            self.add_error("child_subcategory", "Uncategorized cannot have subcategories.")
        tags = cleaned_data.get("tags", [])
        allowed_scopes = {None}
        if subcategory and not new_subcategory:
            allowed_scopes.add(subcategory.pk)
        if child and not new_child and not new_subcategory:
            allowed_scopes.add(child.pk)
        if any(new_category or tag.category_id != getattr(category, "pk", None) or
               tag.subcategory_id not in allowed_scopes for tag in tags):
            self.add_error("tags", "Choose tags from this category or its selected subcategory path.")
        for field in ("new_tags", "new_category_tags", "new_subcategory_tags", "new_child_tags"):
            if any(len(name.strip()) > 255 for name in cleaned_data.get(field, "").split(",")):
                self.add_error(field, "Tag names must contain 255 characters or fewer.")
        if cleaned_data.get("new_subcategory_tags") and not (subcategory or new_subcategory):
            self.add_error("new_subcategory_tags", "Choose or create a subcategory for these tags.")
        if cleaned_data.get("new_child_tags") and not (child or new_child):
            self.add_error("new_child_tags", "Choose or create a second-level subcategory for these tags.")
        if child:
            cleaned_data["subcategory"] = child
        return cleaned_data

    def _get_or_create_by_name(self, model, name, **extra):
        ownership = {"user": self.user}
        existing = model.objects.filter(
            name__iexact=name, **ownership, **extra
        ).first()
        return existing or model.objects.create(
            name=name, **ownership, **extra
        )

    @transaction.atomic
    def save(self, commit=True):
        if not commit:
            raise ValueError("TaxonomyModelForm must be saved with commit=True.")

        category = self.cleaned_data.get("category")
        if not category:
            category = self._get_or_create_by_name(
                self.category_model, self.cleaned_data["new_category"].strip()
            )

        subcategory = self.cleaned_data.get("subcategory")
        new_subcategory = self.cleaned_data.get("new_subcategory", "").strip()
        if new_subcategory:
            subcategory = self._get_or_create_by_name(
                self.subcategory_model, new_subcategory, category=category, parent=None
            )

        new_child = self.cleaned_data.get("new_child_subcategory", "").strip()
        if new_child:
            subcategory = self._get_or_create_by_name(
                self.subcategory_model, new_child, category=category, parent=subcategory,
            )

        record = super().save(commit=False)
        record.category = category
        record.subcategory = subcategory
        record.save()
        record.tags.set(self.cleaned_data.get("tags", []))

        parent_scope = subcategory.parent if subcategory and subcategory.parent_id else subcategory
        child_scope = subcategory if subcategory and subcategory.parent_id else None
        for field, scope in [("new_category_tags", None), ("new_subcategory_tags", parent_scope),
                             ("new_child_tags", child_scope), ("new_tags", subcategory)]:
            names = {name.strip() for name in self.cleaned_data.get(field, "").split(",") if name.strip()}
            for name in names:
                record.tags.add(self._get_or_create_by_name(
                    self.tag_model, name, category=category, subcategory=scope,
                ))
        return record


def taxonomy_form(name, model, category_model, subcategory_model, tag_model):
    meta = type("Meta", (), {
        "model": model,
        "exclude": ("slug", "created_at", "user"),
        "widgets": {"deadline": forms.DateInput(attrs={"type": "date"})},
    })
    return type(name, (TaxonomyModelForm,), {
        "Meta": meta,
        "category_model": category_model,
        "subcategory_model": subcategory_model,
        "tag_model": tag_model,
        "__module__": __name__,
    })


ArticleForm = taxonomy_form("ArticleForm", Article, ArticleCategory, ArticleSubcategory, ArticleTag)
JournalForm = taxonomy_form("JournalForm", Journal, JournalCategory, JournalSubcategory, JournalTag)
NoteForm = taxonomy_form("NoteForm", Note, NoteCategory, NoteSubcategory, NoteTag)
CentralPointForm = taxonomy_form(
    "CentralPointForm", CentralPoint, CentralPointCategory, CentralPointSubcategory, CentralPointTag
)
StrategyForm = taxonomy_form("StrategyForm", Strategy, StrategyCategory, StrategySubcategory, StrategyTag)
DecisionForm = taxonomy_form("DecisionForm", Decision, DecisionCategory, DecisionSubcategory, DecisionTag)
GoalForm = taxonomy_form("GoalForm", Goal, GoalCategory, GoalSubcategory, GoalTag)
