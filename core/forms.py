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
    new_tags = forms.CharField(
        label="New tags",
        required=False,
        help_text="Comma-separated tag names to create and attach.",
    )

    category_model = None
    subcategory_model = None
    tag_model = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].required = False
        self.fields["category"].queryset = self.category_model.objects.order_by("name")
        self.fields["category"].empty_label = "Select an existing category"
        self.fields["subcategory"].queryset = self.subcategory_model.objects.select_related(
            "category"
        ).order_by("category__name", "name")
        self.fields["subcategory"].empty_label = "Select an existing subcategory (optional)"
        self.fields["tags"].queryset = self.tag_model.objects.order_by("name")
        self.fields["tags"].widget = forms.CheckboxSelectMultiple(
            attrs={"class": "tag-choice-input"}
        )
        self.fields["tags"].widget.choices = self.fields["tags"].choices
        self.fields["tags"].help_text = (
            "Tap or click each existing tag you want to attach. You can select multiple tags."
        )

        placeholders = {
            "category": "Select an existing category",
            "subcategory": "Select an existing subcategory (optional)",
            "tags": "Select existing tags",
            "new_category": "Or enter a new category",
            "new_subcategory": "Or enter a new subcategory",
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
        return cleaned_data

    @staticmethod
    def _get_or_create_by_name(model, name, **extra):
        existing = model.objects.filter(name__iexact=name, **extra).first()
        return existing or model.objects.create(name=name, **extra)

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
                self.subcategory_model, new_subcategory, category=category
            )

        record = super().save(commit=False)
        record.category = category
        record.subcategory = subcategory
        record.save()
        record.tags.set(self.cleaned_data.get("tags", []))

        new_tag_names = {
            name.strip() for name in self.cleaned_data.get("new_tags", "").split(",")
            if name.strip()
        }
        for name in new_tag_names:
            record.tags.add(self._get_or_create_by_name(self.tag_model, name))
        return record


def taxonomy_form(name, model, category_model, subcategory_model, tag_model):
    meta = type("Meta", (), {
        "model": model,
        "exclude": ("slug", "created_at"),
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
