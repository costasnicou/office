# from django.contrib import admin
# from django import forms

# from .models import *

# # ARTICLE ADMIN
# class ArticleAdminForm(forms.ModelForm):
#     class Meta:
#         model = Article
#         fields = "__all__"

#     def clean(self):
#         cleaned_data = super().clean()
#         category = cleaned_data.get("category")
#         subcategory = cleaned_data.get("subcategory")

#         if category and subcategory and subcategory.category != category:
#             raise forms.ValidationError("Selected subcategory does not belong to the selected category.")
#         return cleaned_data

# @admin.register(ArticleCategory)
# class ArticleCategoryAdmin(admin.ModelAdmin):
#     list_display = ("name", "slug")
#     search_fields = ("name", "slug")
#     prepopulated_fields = {"slug": ("name",)}

# @admin.register(ArticleSubcategory)
# class ArticleSubcategoryAdmin(admin.ModelAdmin):
#     list_display = ("name", "category", "slug")
#     list_filter = ("category",)
#     search_fields = ("name", "slug", "category__name")
#     prepopulated_fields = {"slug": ("name",)}
#     autocomplete_fields = ("category",)

# @admin.register(ArticleTag)
# class ArticleTagAdmin(admin.ModelAdmin):
#     list_display = ("name", "slug")
#     search_fields = ("name", "slug")
#     prepopulated_fields = {"slug": ("name",)}

# @admin.register(Article)
# class ArticleAdmin(admin.ModelAdmin):
#     form = ArticleAdminForm
#     list_display = ("title", "category", "created_at", "slug")
#     list_filter = ("category", "created_at")
#     search_fields = ("title", "content", "category__name", "tags__name")
#     prepopulated_fields = {"slug": ("title",)}
#     autocomplete_fields = ("category", "tags")
#     filter_horizontal = ("tags",)
#     date_hierarchy = "created_at"
#     ordering = ("-created_at",)

#     def get_queryset(self, request):
#         return super().get_queryset(request).select_related("category").prefetch_related("tags")


# # JOURNAL ADMIN
# class JournalAdminForm(forms.ModelForm):
#     class Meta:
#         model = Journal
#         fields = "__all__"

#     def clean(self):
#         cleaned_data = super().clean()
#         category = cleaned_data.get("category")
#         subcategory = cleaned_data.get("subcategory")

#         if category and subcategory and subcategory.category != category:
#             raise forms.ValidationError("Selected subcategory does not belong to the selected category.")
#         return cleaned_data

# @admin.register(JournalCategory)
# class JournalCategoryAdmin(admin.ModelAdmin):
#     list_display = ("name", "slug")
#     search_fields = ("name", "slug")
#     prepopulated_fields = {"slug": ("name",)}

# @admin.register(JournalSubcategory)
# class JournalSubcategoryAdmin(admin.ModelAdmin):
#     list_display = ("name", "category", "slug")
#     list_filter = ("category",)
#     search_fields = ("name", "slug", "category__name")
#     prepopulated_fields = {"slug": ("name",)}
#     autocomplete_fields = ("category",)

# @admin.register(JournalTag)
# class JournalTagAdmin(admin.ModelAdmin):
#     list_display = ("name", "slug")
#     search_fields = ("name", "slug")
#     prepopulated_fields = {"slug": ("name",)}

# @admin.register(Journal)
# class JournalAdmin(admin.ModelAdmin):
#     form = JournalAdminForm
#     list_display = ("title", "category", "created_at", "slug")
#     list_filter = ("category", "created_at")
#     search_fields = ("title", "content", "category__name", "tags__name")
#     prepopulated_fields = {"slug": ("title",)}
#     autocomplete_fields = ("category", "tags")
#     filter_horizontal = ("tags",)
#     date_hierarchy = "created_at"
#     ordering = ("-created_at",)

#     def get_queryset(self, request):
#         return super().get_queryset(request).select_related("category").prefetch_related("tags")


# # Note ADMIN
# class NoteAdminForm(forms.ModelForm):
#     class Meta:
#         model = Note
#         fields = "__all__"

#     def clean(self):
#         cleaned_data = super().clean()
#         category = cleaned_data.get("category")
#         subcategory = cleaned_data.get("subcategory")

#         if category and subcategory and subcategory.category != category:
#             raise forms.ValidationError("Selected subcategory does not belong to the selected category.")
#         return cleaned_data

# @admin.register(NoteCategory)
# class NoteCategoryAdmin(admin.ModelAdmin):
#     list_display = ("name", "slug")
#     search_fields = ("name", "slug")
#     prepopulated_fields = {"slug": ("name",)}

# @admin.register(NoteSubcategory)
# class NoteSubcategoryAdmin(admin.ModelAdmin):
#     list_display = ("name", "category", "slug")
#     list_filter = ("category",)
#     search_fields = ("name", "slug", "category__name")
#     prepopulated_fields = {"slug": ("name",)}
#     autocomplete_fields = ("category",)

# @admin.register(NoteTag)
# class NoteTagAdmin(admin.ModelAdmin):
#     list_display = ("name", "slug")
#     search_fields = ("name", "slug")
#     prepopulated_fields = {"slug": ("name",)}

# @admin.register(Note)
# class NoteAdmin(admin.ModelAdmin):
#     form = NoteAdminForm
#     list_display = ("title", "category", "created_at", "slug")
#     list_filter = ("category", "created_at")
#     search_fields = ("title", "content", "category__name", "tags__name")
#     prepopulated_fields = {"slug": ("title",)}
#     autocomplete_fields = ("category", "tags")
#     filter_horizontal = ("tags",)
#     date_hierarchy = "created_at"
#     ordering = ("-created_at",)

#     def get_queryset(self, request):
#         return super().get_queryset(request).select_related("category").prefetch_related("tags")


# # CENTRAL POINT ANMIN
# class CentralPointAdminForm(forms.ModelForm):
#     class Meta:
#         model = CentralPoint
#         fields = "__all__"

#     def clean(self):
#         cleaned_data = super().clean()
#         category = cleaned_data.get("category")
#         subcategory = cleaned_data.get("subcategory")

#         if category and subcategory and subcategory.category != category:
#             raise forms.ValidationError("Selected subcategory does not belong to the selected category.")
#         return cleaned_data

# @admin.register(CentralPointCategory)
# class CentralPointCategoryAdmin(admin.ModelAdmin):
#     list_display = ("name", "slug")
#     search_fields = ("name", "slug")
#     prepopulated_fields = {"slug": ("name",)}

# @admin.register(CentralPointSubcategory)
# class CentralPointSubcategoryAdmin(admin.ModelAdmin):
#     list_display = ("name", "category", "slug")
#     list_filter = ("category",)
#     search_fields = ("name", "slug", "category__name")
#     prepopulated_fields = {"slug": ("name",)}
#     autocomplete_fields = ("category",)

# @admin.register(CentralPointTag)
# class CentralPointTagAdmin(admin.ModelAdmin):
#     list_display = ("name", "slug")
#     search_fields = ("name", "slug")
#     prepopulated_fields = {"slug": ("name",)}

# @admin.register(CentralPoint)
# class CentralPointAdmin(admin.ModelAdmin):
#     form = CentralPointAdminForm
#     list_display = ("title", "category", "created_at", "slug")
#     list_filter = ("category", "created_at")
#     search_fields = ("title", "content", "category__name", "tags__name")
#     prepopulated_fields = {"slug": ("title",)}
#     autocomplete_fields = ("category", "tags")
#     filter_horizontal = ("tags",)
#     date_hierarchy = "created_at"
#     ordering = ("-created_at",)

#     def get_queryset(self, request):
#         return super().get_queryset(request).select_related("category").prefetch_related("tags")


# # STRATEGY ADMIN
# class StrategyAdminForm(forms.ModelForm):
#     class Meta:
#         model = Strategy
#         fields = "__all__"

#     def clean(self):
#         cleaned_data = super().clean()
#         category = cleaned_data.get("category")
#         subcategory = cleaned_data.get("subcategory")

#         if category and subcategory and subcategory.category != category:
#             raise forms.ValidationError("Selected subcategory does not belong to the selected category.")
#         return cleaned_data

# @admin.register(StrategyCategory)
# class StrategyCategoryAdmin(admin.ModelAdmin):
#     list_display = ("name", "slug")
#     search_fields = ("name", "slug")
#     prepopulated_fields = {"slug": ("name",)}

# @admin.register(StrategySubcategory)
# class StrategySubcategoryAdmin(admin.ModelAdmin):
#     list_display = ("name", "category", "slug")
#     list_filter = ("category",)
#     search_fields = ("name", "slug", "category__name")
#     prepopulated_fields = {"slug": ("name",)}
#     autocomplete_fields = ("category",)

# @admin.register(StrategyTag)
# class StrategyTagAdmin(admin.ModelAdmin):
#     list_display = ("name", "slug")
#     search_fields = ("name", "slug")
#     prepopulated_fields = {"slug": ("name",)}

# @admin.register(Strategy)
# class StrategyAdmin(admin.ModelAdmin):
#     form = StrategyAdminForm
#     list_display = ("title", "category", "created_at", "slug")
#     list_filter = ("category", "created_at")
#     search_fields = ("title", "content", "category__name", "tags__name")
#     prepopulated_fields = {"slug": ("title",)}
#     autocomplete_fields = ("category", "tags")
#     filter_horizontal = ("tags",)
#     date_hierarchy = "created_at"
#     ordering = ("-created_at",)

#     def get_queryset(self, request):
#         return super().get_queryset(request).select_related("category").prefetch_related("tags")


# # DECISION ADMIN
# class DecisionAdminForm(forms.ModelForm):
#     class Meta:
#         model = Decision
#         fields = "__all__"

#     def clean(self):
#         cleaned_data = super().clean()
#         category = cleaned_data.get("category")
#         subcategory = cleaned_data.get("subcategory")

#         if category and subcategory and subcategory.category != category:
#             raise forms.ValidationError("Selected subcategory does not belong to the selected category.")
#         return cleaned_data

# @admin.register(DecisionCategory)
# class DecisionCategoryAdmin(admin.ModelAdmin):
#     list_display = ("name", "slug")
#     search_fields = ("name", "slug")
#     prepopulated_fields = {"slug": ("name",)}

# @admin.register(DecisionSubcategory)
# class DecisionSubcategoryAdmin(admin.ModelAdmin):
#     list_display = ("name", "category", "slug")
#     list_filter = ("category",)
#     search_fields = ("name", "slug", "category__name")
#     prepopulated_fields = {"slug": ("name",)}
#     autocomplete_fields = ("category",)

# @admin.register(DecisionTag)
# class DecisionTagAdmin(admin.ModelAdmin):
#     list_display = ("name", "slug")
#     search_fields = ("name", "slug")
#     prepopulated_fields = {"slug": ("name",)}

# @admin.register(Decision)
# class DecisionAdmin(admin.ModelAdmin):
#     form = DecisionAdminForm
#     list_display = ("title", "category", "created_at", "slug")
#     list_filter = ("category", "created_at")
#     search_fields = ("title", "content", "category__name", "tags__name")
#     prepopulated_fields = {"slug": ("title",)}
#     autocomplete_fields = ("category", "tags")
#     filter_horizontal = ("tags",)
#     date_hierarchy = "created_at"
#     ordering = ("-created_at",)

#     def get_queryset(self, request):
#         return super().get_queryset(request).select_related("category").prefetch_related("tags")


# # GOAL ADMIN
# class GoalAdminForm(forms.ModelForm):
#     class Meta:
#         model = Goal
#         fields = "__all__"

#     def clean(self):
#         cleaned_data = super().clean()
#         category = cleaned_data.get("category")
#         subcategory = cleaned_data.get("subcategory")

#         if category and subcategory and subcategory.category != category:
#             raise forms.ValidationError("Selected subcategory does not belong to the selected category.")
#         return cleaned_data

# @admin.register(GoalCategory)
# class GoalCategoryAdmin(admin.ModelAdmin):
#     list_display = ("name", "slug")
#     search_fields = ("name", "slug")
#     prepopulated_fields = {"slug": ("name",)}

# @admin.register(GoalSubcategory)
# class GoalSubcategoryAdmin(admin.ModelAdmin):
#     list_display = ("name", "category", "slug")
#     list_filter = ("category",)
#     search_fields = ("name", "slug", "category__name")
#     prepopulated_fields = {"slug": ("name",)}
#     autocomplete_fields = ("category",)

# @admin.register(GoalTag)
# class GoalTagAdmin(admin.ModelAdmin):
#     list_display = ("name", "slug")
#     search_fields = ("name", "slug")
#     prepopulated_fields = {"slug": ("name",)}

# @admin.register(Goal)
# class GoalAdmin(admin.ModelAdmin):
#     form = GoalAdminForm
#     list_display = ("title", "category", "created_at", "slug")
#     list_filter = ("category", "created_at")
#     search_fields = ("title", "content", "category__name", "tags__name")
#     prepopulated_fields = {"slug": ("title",)}
#     autocomplete_fields = ("category", "tags")
#     filter_horizontal = ("tags",)
#     date_hierarchy = "created_at"
#     ordering = ("-created_at",)

#     def get_queryset(self, request):
#         return super().get_queryset(request).select_related("category").prefetch_related("tags")


# # ARTICLES
# # ArticleCategory._meta.app_label = "Articles"
# # ArticleSubcategory._meta.app_label = "Articles"
# # ArticleTag._meta.app_label = "Articles"
# # Article._meta.app_label = "Articles"

# # # JOURNALS
# # JournalCategory._meta.app_label = "Journals"
# # JournalSubcategory._meta.app_label = "Journals"
# # JournalTag._meta.app_label = "Journals"
# # Journal._meta.app_label = "Journals"

# # # NOTES
# # NoteCategory._meta.app_label = "Notes"
# # NoteSubcategory._meta.app_label = "Notes"
# # NoteTag._meta.app_label = "Notes"
# # Note._meta.app_label = "Notes"

# # # CENTRAL POINTS
# # CentralPointCategory._meta.app_label = "CentralPoints"
# # CentralPointSubcategory._meta.app_label = "CentralPoints"
# # CentralPointTag._meta.app_label = "CentralPoints"
# # CentralPoint._meta.app_label = "CentralPoints"

# # # STRATEGIES
# # StrategyCategory._meta.app_label = "Strategies"
# # StrategySubcategory._meta.app_label = "Strategies"
# # StrategyTag._meta.app_label = "Strategies"
# # Strategy._meta.app_label = "Strategies"

# # # DECISIONS
# # DecisionCategory._meta.app_label = "Decisions"
# # DecisionSubcategory._meta.app_label = "Decisions"
# # DecisionTag._meta.app_label = "Decisions"
# # Decision._meta.app_label = "Decisions"

# # # GOALS
# # GoalCategory._meta.app_label = "Goals"
# # GoalSubcategory._meta.app_label = "Goals"
# # GoalTag._meta.app_label = "Goals"
# # Goal._meta.app_label = "Goals"

# # admin.py

# from .admin_site import admin_site

# admin_site.register(Article, ArticleAdmin)
# admin_site.register(ArticleCategory, ArticleCategoryAdmin)
# admin_site.register(ArticleSubcategory, ArticleSubcategoryAdmin)
# admin_site.register(ArticleTag, ArticleTagAdmin)

# # register the rest the same way...
from django import forms
from django.contrib import admin
from .admin_site import admin_site  # Importing your custom admin site
from .models import (
    Article, ArticleCategory, ArticleSubcategory, ArticleTag,
    Journal, JournalCategory, JournalSubcategory, JournalTag,
    Note, NoteCategory, NoteSubcategory, NoteTag,
    CentralPoint, CentralPointCategory, CentralPointSubcategory, CentralPointTag,
    Strategy, StrategyCategory, StrategySubcategory, StrategyTag,
    Decision, DecisionCategory, DecisionSubcategory, DecisionTag,
    Goal, GoalCategory, GoalSubcategory, GoalTag,
)

# 1. Base Form Factory
def create_admin_form(model_class):
    class DynamicAdminForm(forms.ModelForm):
        class Meta:
            model = model_class
            fields = "__all__"

        def clean(self):
            cleaned_data = super().clean()
            category = cleaned_data.get("category")
            subcategory = cleaned_data.get("subcategory")

            if category and subcategory and subcategory.category != category:
                raise forms.ValidationError(
                    "Selected subcategory does not belong to the selected category."
                )
            return cleaned_data
            
    return DynamicAdminForm


# 2. Base Admin Classes
class BaseCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}


class BaseSubcategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "slug")
    list_filter = ("category",)
    search_fields = ("name", "slug", "category__name")
    prepopulated_fields = {"slug": ("name",)}
    autocomplete_fields = ("category",)


class BaseTagAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}


class BaseContentAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "created_at", "slug")
    list_filter = ("category", "created_at")
    search_fields = ("title", "content", "category__name", "tags__name")
    prepopulated_fields = {"slug": ("title",)}
    autocomplete_fields = ("category", "tags")
    filter_horizontal = ("tags",)
    date_hierarchy = "created_at"
    ordering = ("-created_at",)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("category").prefetch_related("tags")


# 3. Define content groups to register automatically
CONTENT_GROUPS = [
    ("Article", Article, ArticleCategory, ArticleSubcategory, ArticleTag),
    ("Journal", Journal, JournalCategory, JournalSubcategory, JournalTag),
    ("Note", Note, NoteCategory, NoteSubcategory, NoteTag),
    ("CentralPoint", CentralPoint, CentralPointCategory, CentralPointSubcategory, CentralPointTag),
    ("Strategy", Strategy, StrategyCategory, StrategySubcategory, StrategyTag),
    ("Decision", Decision, DecisionCategory, DecisionSubcategory, DecisionTag),
    ("Goal", Goal, GoalCategory, GoalSubcategory, GoalTag),
]

# 4. Loop and dynamically register everything to your custom admin_site
for prefix, main_model, cat_model, subcat_model, tag_model in CONTENT_GROUPS:
    
    # Dynamically create the custom ModelAdmin for the main content type
    custom_admin_class = type(
        f"{prefix}Admin",
        (BaseContentAdmin,),
        {"form": create_admin_form(main_model)}
    )
    
    # Register everything into your custom admin_site
    admin_site.register(main_model, custom_admin_class)
    admin_site.register(cat_model, BaseCategoryAdmin)
    admin_site.register(subcat_model, BaseSubcategoryAdmin)
    admin_site.register(tag_model, BaseTagAdmin)