from django.test import TestCase
from django.urls import reverse
from unittest.mock import patch

from .forms import ArticleForm, RegistrationForm
from .models import (
    Article, ArticleCategory, ArticleSubcategory, ArticleTag, Strategy, User,
)


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


class RegistrationTests(TestCase):
    def test_registration_page_is_public_and_responsive(self):
        response = self.client.get(reverse("register"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="viewport"')
        self.assertContains(response, 'class="register-grid"')
        self.assertContains(response, reverse("google_login"))

    def test_creates_and_signs_in_a_local_user(self):
        response = self.client.post(reverse("register"), {
            "first_name": "Ada",
            "last_name": "Lovelace",
            "username": "ada",
            "email": "ADA@example.com",
            "password1": "A-complex-password-1865",
            "password2": "A-complex-password-1865",
        })

        user = User.objects.get(username="ada")
        self.assertEqual(user.first_name, "Ada")
        self.assertEqual(user.last_name, "Lovelace")
        self.assertEqual(user.email, "ada@example.com")
        self.assertEqual(self.client.session["_auth_user_id"], str(user.pk))
        self.assertRedirects(response, reverse("index"))

    def test_rejects_an_email_that_is_already_registered(self):
        User.objects.create_user(
            username="existing",
            email="person@example.com",
            password="A-complex-password-1865",
        )
        form = RegistrationForm(data={
            "first_name": "New",
            "last_name": "Person",
            "username": "new-person",
            "email": "PERSON@example.com",
            "password1": "A-complex-password-1865",
            "password2": "A-complex-password-1865",
        })

        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)

    @patch("core.views.fetch_profile")
    def test_google_callback_creates_and_signs_in_user(self, fetch_profile):
        fetch_profile.return_value = {
            "email": "grace@example.com",
            "email_verified": True,
            "given_name": "Grace",
            "family_name": "Hopper",
        }
        session = self.client.session
        session["google_oauth_state"] = "secure-state"
        session.save()

        response = self.client.get(reverse("google_callback"), {
            "state": "secure-state",
            "code": "google-code",
        })

        user = User.objects.get(email="grace@example.com")
        self.assertEqual(user.first_name, "Grace")
        self.assertFalse(user.has_usable_password())
        self.assertEqual(self.client.session["_auth_user_id"], str(user.pk))
        self.assertRedirects(response, reverse("index"))

    @patch("core.views.fetch_profile")
    def test_google_callback_rejects_an_invalid_state(self, fetch_profile):
        session = self.client.session
        session["google_oauth_state"] = "expected-state"
        session.save()

        response = self.client.get(reverse("google_callback"), {
            "state": "wrong-state",
            "code": "google-code",
        })

        fetch_profile.assert_not_called()
        self.assertRedirects(response, reverse("register"))


class RecordSearchTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="searcher", password="test-password")
        self.client.force_login(self.user)

    def test_searches_titles_across_post_types_and_links_to_the_correct_single_view(self):
        strategy = Strategy.objects.create(
            title="Competitor growth plan",
            threats="A market threat",
            finalized_strategy="Expand carefully",
        )

        response = self.client.get(reverse("record_search"), {"q": "competitor"})

        self.assertContains(response, strategy.title)
        self.assertContains(response, reverse("strategy_single", args=[strategy.slug]))

    def test_does_not_search_post_content(self):
        strategy = Strategy.objects.create(
            title="Growth plan",
            threats="A uniquely searchable competitor",
            finalized_strategy="Expand carefully",
        )

        response = self.client.get(reverse("record_search"), {"q": "competitor"})

        self.assertNotContains(response, strategy.title)
        self.assertNotContains(response, reverse("strategy_single", args=[strategy.slug]))

    def test_combines_post_types_in_reverse_chronological_order(self):
        category = ArticleCategory.objects.create(name="Work")
        article = Article.objects.create(
            title="Earlier shared record",
            content="Article body",
            category=category,
        )
        strategy = Strategy.objects.create(
            title="Later shared record",
            finalized_strategy="Strategy body",
        )

        response = self.client.get(reverse("record_search"), {"q": "shared"})

        self.assertContains(response, reverse("article_single", args=[article.slug]))
        self.assertContains(response, reverse("strategy_single", args=[strategy.slug]))
        self.assertLess(
            response.content.index(strategy.title.encode()),
            response.content.index(article.title.encode()),
        )

    def test_search_requires_login(self):
        self.client.logout()

        response = self.client.get(reverse("record_search"), {"q": "anything"})

        self.assertRedirects(
            response,
            f'{reverse("login")}?next={reverse("record_search")}%3Fq%3Danything',
        )


class RecordUpdateTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="editor", password="test-password")
        self.category = ArticleCategory.objects.create(name="Work")
        self.article = Article.objects.create(
            title="Original title",
            content="Original body",
            category=self.category,
        )

    def test_edit_page_requires_login(self):
        edit_url = reverse("article_edit", args=[self.article.slug])

        response = self.client.get(edit_url)

        self.assertRedirects(response, f'{reverse("login")}?next={edit_url}')

    def test_edit_page_prefills_existing_record(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("article_edit", args=[self.article.slug]))

        self.assertContains(response, 'value="Original title"')
        self.assertContains(response, "Original body")
        self.assertContains(response, "Delete Article")

    def test_updates_record_and_redirects_to_single_page(self):
        self.client.force_login(self.user)

        response = self.client.post(reverse("article_edit", args=[self.article.slug]), {
            "title": "Updated title",
            "content": "Updated body",
            "category": self.category.pk,
        })

        self.article.refresh_from_db()
        self.assertEqual(self.article.title, "Updated title")
        self.assertEqual(self.article.content, "Updated body")
        self.assertRedirects(
            response,
            reverse("article_single", args=[self.article.slug]),
        )

    def test_deletes_record_with_post_and_redirects_to_index(self):
        self.client.force_login(self.user)

        response = self.client.post(reverse("article_edit", args=[self.article.slug]), {
            "action": "delete",
        })

        self.assertFalse(Article.objects.filter(pk=self.article.pk).exists())
        self.assertRedirects(response, reverse("index"))

    def test_every_single_template_has_its_edit_link(self):
        edit_routes = {
            "article": "article_edit",
            "journal": "journal_edit",
            "note": "note_edit",
            "centralpoint": "centralpoint_edit",
            "strategy": "strategy_edit",
            "decision": "decision_edit",
            "goal": "goal_edit",
        }

        for record_type, route_name in edit_routes.items():
            with self.subTest(record_type=record_type):
                template_path = f"core/templates/core/singles/{record_type}-single.html"
                with open(template_path, encoding="utf-8") as template:
                    self.assertIn(f"{{% url '{route_name}' article.slug %}}", template.read())
