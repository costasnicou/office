from django.test import TestCase
from django.urls import reverse

from .forms import ArticleForm
from .models import Article, ArticleCategory, ArticleSubcategory, ArticleTag, User


class ArticleCreateTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="writer", password="test-password")

    def test_create_page_requires_login(self):
        response = self.client.get(reverse("article_create"))
        self.assertRedirects(
            response,
            f'{reverse("login")}?next={reverse("article_create")}',
        )

    def test_create_page_does_not_render_empty_error_lists(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("article_create"))

        self.assertNotContains(response, 'class="field-errors"')

    def test_create_page_renders_actual_field_errors(self):
        self.client.force_login(self.user)

        response = self.client.post(reverse("article_create"), {"title": ""})

        self.assertContains(response, 'class="field-errors"')
        self.assertContains(response, "This field is required.")

    def test_creates_record_and_new_taxonomy_values(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse("article_create"), {
            "title": "Useful article",
            "content": "Article body",
            "new_category": "Work",
            "new_subcategory": "Planning",
            "new_tags": "Important, Weekly",
        })

        article = Article.objects.get(title="Useful article")
        self.assertRedirects(response, reverse("article_single", args=[article.slug]))
        self.assertEqual(article.category.name, "Work")
        self.assertEqual(article.subcategory.name, "Planning")
        self.assertCountEqual(article.tags.values_list("name", flat=True), ["Important", "Weekly"])

    def test_reuses_existing_values_case_insensitively(self):
        category = ArticleCategory.objects.create(name="Work")
        tag = ArticleTag.objects.create(name="Important")
        form = ArticleForm(data={
            "title": "Another article",
            "content": "Body",
            "category": category.pk,
            "new_tags": "important",
        })

        self.assertTrue(form.is_valid(), form.errors)
        article = form.save()
        self.assertEqual(article.tags.get(), tag)
        self.assertEqual(ArticleTag.objects.count(), 1)

    def test_selects_existing_tags(self):
        category = ArticleCategory.objects.create(name="Work")
        first_tag = ArticleTag.objects.create(name="Important")
        second_tag = ArticleTag.objects.create(name="Reference")
        form = ArticleForm(data={
            "title": "Tagged article",
            "content": "Body",
            "category": category.pk,
            "tags": [first_tag.pk, second_tag.pk],
        })

        self.assertTrue(form.is_valid(), form.errors)
        article = form.save()
        self.assertCountEqual(article.tags.all(), [first_tag, second_tag])

    def test_existing_tags_are_rendered_as_touch_friendly_checkboxes(self):
        ArticleTag.objects.create(name="Important")
        ArticleTag.objects.create(name="Reference")

        rendered_tags = str(ArticleForm()["tags"])

        self.assertIn('type="checkbox"', rendered_tags)
        self.assertIn("Important", rendered_tags)
        self.assertIn("Reference", rendered_tags)

    def test_rejects_subcategory_from_another_category(self):
        selected_category = ArticleCategory.objects.create(name="Work")
        other_category = ArticleCategory.objects.create(name="Personal")
        subcategory = ArticleSubcategory.objects.create(
            category=other_category,
            name="Health",
        )
        form = ArticleForm(data={
            "title": "Invalid article",
            "content": "Body",
            "category": selected_category.pk,
            "subcategory": subcategory.pk,
        })

        self.assertFalse(form.is_valid())
        self.assertIn("subcategory", form.errors)
