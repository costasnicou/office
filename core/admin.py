from django.contrib import admin
from django import forms

from .models import Article, ArticleCategory, ArticleSubcategory, ArticleTag


class ArticleAdminForm(forms.ModelForm):
    class Meta:
        model = Article
        fields = "__all__"

    def clean(self):
        cleaned_data = super().clean()
        category = cleaned_data.get("category")
        subcategory = cleaned_data.get("subcategory")

        if category and subcategory and subcategory.category != category:
            raise forms.ValidationError("Selected subcategory does not belong to the selected category.")
        return cleaned_data


@admin.register(ArticleCategory)
class ArticleCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(ArticleSubcategory)
class ArticleSubcategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "slug")
    list_filter = ("category",)
    search_fields = ("name", "slug", "category__name")
    prepopulated_fields = {"slug": ("name",)}
    autocomplete_fields = ("category",)


@admin.register(ArticleTag)
class ArticleTagAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    form = ArticleAdminForm
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