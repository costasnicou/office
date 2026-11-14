import base64
from datetime import date
import tempfile
from django.conf import settings
from django.test import TestCase, TransactionTestCase, override_settings
from django.db import connection, transaction
from django.db.migrations.executor import MigrationExecutor
from django.urls import reverse
from django.core.management import call_command
from django.core.files.uploadedfile import SimpleUploadedFile
from unittest.mock import patch
from io import StringIO

from .forms import ArticleForm, RegistrationForm
from .models import (
    Article, ArticleCategory, ArticleSubcategory, ArticleTag, RecordDraft,
    Strategy, User,
)
from .views import TAXONOMY_MODELS


def workspace_reverse(name, user, args=None):
    return reverse(name, args=[user.username, *(args or [])])


class CKEditorUploadTests(TestCase):
    PNG_DATA = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwC"
        "AAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
    )

    def setUp(self):
        self.user = User.objects.create_user(
            username="ckeditor-user",
            password="test-password",
        )

    def test_authenticated_user_can_upload_an_image(self):
        self.client.force_login(self.user)

        with tempfile.TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                response = self.client.post(
                    reverse("ck_editor_5_upload_file"),
                    {
                        "upload": SimpleUploadedFile(
                            "pixel.png",
                            self.PNG_DATA,
                            content_type="image/png",
                        ),
                    },
                )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["url"].startswith("/media/"))

    def test_anonymous_user_cannot_upload_an_image(self):
        response = self.client.post(reverse("ck_editor_5_upload_file"))

        self.assertEqual(response.status_code, 403)

    def test_media_embed_is_enabled_for_all_editor_configurations(self):
        for config_name in ("default", "extends"):
            with self.subTest(config_name=config_name):
                config = settings.CKEDITOR_5_CONFIGS[config_name]
                self.assertIn("mediaEmbed", config["toolbar"])
                self.assertTrue(config["mediaEmbed"]["previewsInData"])

    def test_cross_origin_media_receives_origin_referrer_policy(self):
        response = self.client.get(reverse("login"))

        self.assertEqual(
            response.headers["Referrer-Policy"],
            "strict-origin-when-cross-origin",
        )


class ArticleCreateTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="writer", password="test-password")

    def test_create_page_requires_login(self):
        response = self.client.get(workspace_reverse("article_create", self.user))
        self.assertRedirects(
            response,
            f'{reverse("login")}?next={workspace_reverse("article_create", self.user)}',
        )

    def test_create_page_does_not_render_empty_error_lists(self):
        self.client.force_login(self.user)

        response = self.client.get(workspace_reverse("article_create", self.user))

        self.assertNotContains(response, 'class="field-errors"')

    def test_create_page_renders_actual_field_errors(self):
        self.client.force_login(self.user)

        response = self.client.post(workspace_reverse("article_create", self.user), {"title": ""})

        self.assertContains(response, 'class="field-errors"')
        self.assertContains(response, "This field is required.")

    def test_autosave_stores_an_incomplete_new_record_as_a_draft(self):
        self.client.force_login(self.user)

        response = self.client.post(
            workspace_reverse("record_autosave", self.user, args=["article"]),
            {"title": "Work in progress", "content": "Unfinished body"},
        )

        self.assertEqual(response.status_code, 200)
        draft = RecordDraft.objects.get(
            user=self.user, record_type="article", record_key="__new__"
        )
        self.assertEqual(draft.data["title"], ["Work in progress"])
        self.assertFalse(Article.objects.exists())

    def test_create_page_restores_the_users_draft(self):
        RecordDraft.objects.create(
            user=self.user,
            record_type="article",
            data={"title": ["Restored title"], "content": ["Restored body"]},
        )
        self.client.force_login(self.user)

        response = self.client.get(workspace_reverse("article_create", self.user))

        self.assertContains(response, 'value="Restored title"')
        self.assertContains(response, "Restored body")
        self.assertContains(response, "Draft restored")

    def test_final_save_removes_the_new_record_draft(self):
        RecordDraft.objects.create(
            user=self.user,
            record_type="article",
            data={"title": ["Draft title"]},
        )
        self.client.force_login(self.user)

        self.client.post(workspace_reverse("article_create", self.user), {
            "title": "Published title",
            "content": "Published body",
            "new_category": "Work",
        })

        self.assertTrue(Article.objects.filter(title="Published title").exists())
        self.assertFalse(RecordDraft.objects.filter(user=self.user).exists())

    def test_autosave_cannot_modify_another_users_record(self):
        other_user = User.objects.create_user(username="other-writer")
        category = ArticleCategory.objects.create(user=other_user, name="Private")
        article = Article.objects.create(
            user=other_user,
            title="Private article",
            content="Private body",
            category=category,
        )
        self.client.force_login(self.user)

        response = self.client.post(
            workspace_reverse("record_autosave", self.user, args=["article"]),
            {"record_slug": article.slug, "title": "Attempted overwrite"},
        )

        self.assertEqual(response.status_code, 404)
        self.assertFalse(RecordDraft.objects.exists())

    def test_edit_autosave_does_not_change_record_until_final_save(self):
        category = ArticleCategory.objects.create(user=self.user, name="Work")
        article = Article.objects.create(
            user=self.user,
            title="Published title",
            content="Published body",
            category=category,
        )
        self.client.force_login(self.user)

        response = self.client.post(
            workspace_reverse("record_autosave", self.user, args=["article"]),
            {
                "record_slug": article.slug,
                "title": "Draft edit",
                "content": "Draft body",
                "category": str(category.pk),
            },
        )

        self.assertEqual(response.status_code, 200)
        article.refresh_from_db()
        self.assertEqual(article.title, "Published title")
        draft = RecordDraft.objects.get(record_key=article.slug)
        self.assertEqual(draft.data["title"], ["Draft edit"])

    def test_creates_record_and_new_taxonomy_values(self):
        self.client.force_login(self.user)
        response = self.client.post(workspace_reverse("article_create", self.user), {
            "title": "Useful article",
            "content": "Article body",
            "new_category": "Work",
            "new_subcategory": "Planning",
            "new_tags": "Important, Weekly",
        })

        article = Article.objects.get(title="Useful article")
        self.assertRedirects(response, workspace_reverse("article_single", self.user, args=[article.slug]))
        self.assertEqual(article.user, self.user)
        self.assertEqual(article.category.name, "Work")
        self.assertEqual(article.category.user, self.user)
        self.assertEqual(article.subcategory.name, "Planning")
        self.assertEqual(article.subcategory.user, self.user)
        self.assertCountEqual(article.tags.values_list("name", flat=True), ["Important", "Weekly"])
        self.assertFalse(article.tags.exclude(user=self.user).exists())

    def test_reuses_existing_values_case_insensitively(self):
        category = ArticleCategory.objects.create(name="Work")
        tag = ArticleTag.objects.create(category=category, name="Important")
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
        first_tag = ArticleTag.objects.create(category=category, name="Important")
        second_tag = ArticleTag.objects.create(category=category, name="Reference")
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
        category = ArticleCategory.objects.create(name="Work")
        ArticleTag.objects.create(category=category, name="Important")
        ArticleTag.objects.create(category=category, name="Reference")

        rendered_tags = str(ArticleForm()["tags"])

        self.assertIn('type="checkbox"', rendered_tags)
        self.assertIn("Important", rendered_tags)
        self.assertIn("Reference", rendered_tags)

    def test_create_form_only_shows_the_logged_in_users_taxonomy(self):
        other_user = User.objects.create_user(username="taxonomy-other")
        ArticleCategory.objects.create(user=self.user, name="My category")
        ArticleCategory.objects.create(user=other_user, name="Other category")
        ArticleTag.objects.create(user=self.user, category=ArticleCategory.objects.get(user=self.user, name="My category"), name="My tag")
        ArticleTag.objects.create(user=other_user, category=ArticleCategory.objects.get(user=other_user, name="Other category"), name="Other tag")
        self.client.force_login(self.user)

        response = self.client.get(workspace_reverse("article_create", self.user))

        self.assertContains(response, "My category")
        self.assertContains(response, "My tag")
        self.assertNotContains(response, "Other category")
        self.assertNotContains(response, "Other tag")

    def test_users_can_create_taxonomy_with_the_same_name(self):
        other_user = User.objects.create_user(username="same-name-other")
        ArticleCategory.objects.create(user=other_user, name="Work")
        ArticleTag.objects.create(user=other_user, category=ArticleCategory.objects.get(user=other_user, name="Work"), name="Important")
        self.client.force_login(self.user)

        response = self.client.post(workspace_reverse("article_create", self.user), {
            "title": "My independently categorized article",
            "content": "Body",
            "new_category": "Work",
            "new_tags": "Important",
        })

        article = Article.objects.get(title="My independently categorized article")
        self.assertRedirects(response, workspace_reverse("article_single", self.user, args=[article.slug]))
        self.assertEqual(article.category.user, self.user)
        self.assertEqual(article.tags.get().user, self.user)

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

    def test_creates_account_and_redirects_to_login_without_signing_in(self):
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
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertRedirects(response, reverse("login"))

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
        self.assertRedirects(response, workspace_reverse("index", user))

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


class LoginTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="email-user",
            email="person@example.com",
            password="test-password",
        )

    def test_signs_in_with_email_case_insensitively(self):
        response = self.client.post(reverse("login"), {
            "username": "PERSON@EXAMPLE.COM",
            "password": "test-password",
        })

        self.assertEqual(self.client.session["_auth_user_id"], str(self.user.pk))
        self.assertRedirects(response, workspace_reverse("index", self.user))

    @override_settings(
        AUTHENTICATION_BACKENDS=["django.contrib.auth.backends.ModelBackend"]
    )
    def test_email_login_is_resolved_before_calling_the_authentication_backend(self):
        response = self.client.post(reverse("login"), {
            "username": "person@example.com",
            "password": "test-password",
        })

        self.assertEqual(self.client.session["_auth_user_id"], str(self.user.pk))
        self.assertRedirects(response, workspace_reverse("index", self.user))

    def test_still_signs_in_with_username(self):
        response = self.client.post(reverse("login"), {
            "username": "email-user",
            "password": "test-password",
        })

        self.assertEqual(self.client.session["_auth_user_id"], str(self.user.pk))
        self.assertRedirects(response, workspace_reverse("index", self.user))

    def test_login_page_explains_that_email_is_supported(self):
        response = self.client.get(reverse("login"))

        self.assertContains(response, "Username or email")


class RecordSearchTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="searcher", password="test-password")
        self.client.force_login(self.user)

    def test_searches_titles_across_post_types_and_links_to_the_correct_single_view(self):
        strategy = Strategy.objects.create(
            user=self.user,
            title="Competitor growth plan",
            threats="A market threat",
            finalized_strategy="Expand carefully",
        )

        response = self.client.get(workspace_reverse("record_search", self.user), {"q": "competitor"})

        self.assertContains(response, strategy.title)
        self.assertContains(response, workspace_reverse("strategy_single", self.user, args=[strategy.slug]))

    def test_does_not_search_post_content(self):
        strategy = Strategy.objects.create(
            user=self.user,
            title="Growth plan",
            threats="A uniquely searchable competitor",
            finalized_strategy="Expand carefully",
        )

        response = self.client.get(workspace_reverse("record_search", self.user), {"q": "competitor"})

        self.assertNotContains(response, strategy.title)
        self.assertNotContains(response, workspace_reverse("strategy_single", self.user, args=[strategy.slug]))

    def test_search_only_returns_the_logged_in_users_records(self):
        other_user = User.objects.create_user(username="other", password="test-password")
        own_strategy = Strategy.objects.create(
            user=self.user,
            title="Private growth plan",
            threats="",
            finalized_strategy="Own record",
        )
        Strategy.objects.create(
            user=other_user,
            title="Private competitor plan",
            threats="",
            finalized_strategy="Another user's record",
        )

        response = self.client.get(workspace_reverse("record_search", self.user), {"q": "private"})

        self.assertContains(response, own_strategy.title)
        self.assertNotContains(response, "Private competitor plan")


class RecordOwnershipTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="owner", password="test-password")
        self.other_user = User.objects.create_user(username="other-owner", password="test-password")
        self.category = ArticleCategory.objects.create(user=self.user, name="Private")
        self.own_article = Article.objects.create(
            user=self.user,
            title="My article",
            content="Mine",
            category=self.category,
        )
        self.other_article = Article.objects.create(
            user=self.other_user,
            title="Someone else's article",
            content="Theirs",
            category=self.category,
        )
        self.client.force_login(self.user)

    def test_index_only_shows_the_logged_in_users_records(self):
        response = self.client.get(workspace_reverse("index", self.user))

        self.assertContains(response, self.own_article.title)
        self.assertNotContains(response, self.other_article.title)

    def test_cannot_view_another_users_record(self):
        response = self.client.get(
            workspace_reverse("article_single", self.user, args=[self.other_article.slug])
        )

        self.assertEqual(response.status_code, 404)

    def test_cannot_use_another_users_workspace_url(self):
        response = self.client.get(workspace_reverse("index", self.other_user))

        self.assertEqual(response.status_code, 404)

    def test_cannot_edit_or_delete_another_users_record(self):
        url = workspace_reverse("article_edit", self.user, args=[self.other_article.slug])

        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(
            self.client.post(url, {"action": "delete"}).status_code,
            404,
        )
        self.assertTrue(Article.objects.filter(pk=self.other_article.pk).exists())

    def test_combines_post_types_in_reverse_chronological_order(self):
        category = ArticleCategory.objects.create(name="Work")
        article = Article.objects.create(
            user=self.user,
            title="Earlier shared record",
            content="Article body",
            category=category,
        )
        strategy = Strategy.objects.create(
            user=self.user,
            title="Later shared record",
            finalized_strategy="Strategy body",
        )

        response = self.client.get(workspace_reverse("record_search", self.user), {"q": "shared"})

        self.assertContains(response, workspace_reverse("article_single", self.user, args=[article.slug]))
        self.assertContains(response, workspace_reverse("strategy_single", self.user, args=[strategy.slug]))
        self.assertLess(
            response.content.index(strategy.title.encode()),
            response.content.index(article.title.encode()),
        )

    def test_search_requires_login(self):
        self.client.logout()

        response = self.client.get(workspace_reverse("record_search", self.user), {"q": "anything"})

        self.assertRedirects(
            response,
            f'{reverse("login")}?next={workspace_reverse("record_search", self.user)}%3Fq%3Danything',
        )


class RecordUpdateTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="editor", password="test-password")
        self.category = ArticleCategory.objects.create(user=self.user, name="Work")
        self.article = Article.objects.create(
            user=self.user,
            title="Original title",
            content="Original body",
            category=self.category,
        )

    def test_edit_page_requires_login(self):
        edit_url = workspace_reverse("article_edit", self.user, args=[self.article.slug])

        response = self.client.get(edit_url)

        self.assertRedirects(response, f'{reverse("login")}?next={edit_url}')

    def test_edit_page_prefills_existing_record(self):
        self.client.force_login(self.user)

        response = self.client.get(workspace_reverse("article_edit", self.user, args=[self.article.slug]))

        self.assertContains(response, 'value="Original title"')
        self.assertContains(response, "Original body")
        self.assertContains(response, "Delete Article")

    def test_updates_record_and_redirects_to_single_page(self):
        self.client.force_login(self.user)

        response = self.client.post(workspace_reverse("article_edit", self.user, args=[self.article.slug]), {
            "title": "Updated title",
            "content": "Updated body",
            "category": self.category.pk,
        })

        self.article.refresh_from_db()
        self.assertEqual(self.article.title, "Updated title")
        self.assertEqual(self.article.content, "Updated body")
        self.assertRedirects(
            response,
            workspace_reverse("article_single", self.user, args=[self.article.slug]),
        )

    def test_deletes_record_with_post_and_redirects_to_index(self):
        self.client.force_login(self.user)

        response = self.client.post(workspace_reverse("article_edit", self.user, args=[self.article.slug]), {
            "action": "delete",
        })

        self.assertFalse(Article.objects.filter(pk=self.article.pk).exists())
        self.assertRedirects(response, workspace_reverse("index", self.user))

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
                    self.assertIn(
                        f"{{% url '{route_name}' request.user.username article.slug %}}",
                        template.read(),
                    )


class TaxonomyPopupTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="taxonomy-owner",
            password="test-password",
        )
        self.other_user = User.objects.create_user(
            username="taxonomy-other-owner",
            password="test-password",
        )
        self.client.force_login(self.user)

    def taxonomy_url(self, record_type, user=None):
        return workspace_reverse(
            "taxonomy_create",
            user or self.user,
            args=[record_type],
        )

    def taxonomy_delete_url(self, record_type, user=None):
        return workspace_reverse(
            "taxonomy_delete",
            user or self.user,
            args=[record_type],
        )

    def test_sign_in_creates_default_category_for_every_record_type(self):
        for record_type, models_for_type in TAXONOMY_MODELS.items():
            _, category_model, _, _ = models_for_type
            with self.subTest(record_type=record_type):
                self.assertTrue(category_model.objects.filter(
                    user=self.user,
                    name="Uncategorized",
                    slug="uncategorized",
                ).exists())

    def test_uncategorized_is_the_first_category_in_forms_and_sidebars(self):
        ArticleCategory.objects.create(user=self.user, name="Alpha")

        form = ArticleForm(user=self.user)
        response = self.client.get(workspace_reverse("index", self.user))

        self.assertEqual(
            form.fields["category"].queryset.first().slug,
            "uncategorized",
        )
        self.assertEqual(
            response.context["article_categories"].first().slug,
            "uncategorized",
        )

    def test_workspace_renders_reusable_taxonomy_modal_and_controls_script(self):
        response = self.client.get(workspace_reverse("index", self.user))

        self.assertContains(response, 'class="taxonomy-modal"')
        self.assertContains(response, 'class="sidebar-toggle"')
        self.assertContains(response, 'data-record-type="article"')
        self.assertContains(response, "js/taxonomy-menu.js")
        self.assertContains(response, "taxonomy-menu.js?v=20261113-4")
        self.assertContains(response, "google-translate.js?v=20260726-1")
        self.assertContains(response, 'id="google_translate_element"', count=1)
        self.assertContains(response, 'data-language="en"', count=1)
        self.assertContains(response, 'data-language="el"', count=1)
        self.assertNotContains(response, 'class="language-flag" type="button" data-language="en" aria-label="English" title="English" disabled')
        self.assertLess(
            response.content.index(b'class="logout"'),
            response.content.index(b'class="language-selector'),
        )

    def test_record_create_and_edit_forms_hide_sidebar_toggle(self):
        category = ArticleCategory.objects.get(
            user=self.user,
            slug="uncategorized",
        )
        article = Article.objects.create(
            user=self.user,
            category=category,
            title="Record being edited",
            content="Body",
        )

        create_response = self.client.get(
            workspace_reverse("article_create", self.user)
        )
        edit_response = self.client.get(
            workspace_reverse("article_edit", self.user, args=[article.slug])
        )

        self.assertNotContains(create_response, 'class="sidebar-toggle"')
        self.assertNotContains(edit_response, 'class="sidebar-toggle"')

    def test_single_record_page_uses_collapsible_desktop_sidebar(self):
        category = ArticleCategory.objects.get(
            user=self.user,
            slug="uncategorized",
        )
        article = Article.objects.create(
            user=self.user,
            category=category,
            title="Single page sidebar",
            content="Body",
        )

        response = self.client.get(
            workspace_reverse("article_single", self.user, args=[article.slug])
        )

        self.assertContains(
            response,
            'class="workspace-page workspace-single-page"',
        )
        self.assertContains(response, 'class="sidebar-toggle"')

    def test_creates_user_owned_taxonomy_for_every_record_type(self):
        for record_type, models_for_type in TAXONOMY_MODELS.items():
            _, category_model, subcategory_model, tag_model = models_for_type
            with self.subTest(record_type=record_type, kind="category"):
                response = self.client.post(self.taxonomy_url(record_type), {
                    "kind": "category",
                    "name": f"{record_type} category",
                })
                self.assertEqual(response.status_code, 200)
                category = category_model.objects.get(
                    user=self.user,
                    name=f"{record_type} category",
                )

            with self.subTest(record_type=record_type, kind="subcategory"):
                response = self.client.post(self.taxonomy_url(record_type), {
                    "kind": "subcategory",
                    "name": f"{record_type} subcategory",
                    "category_slug": category.slug,
                })
                self.assertEqual(response.status_code, 200)
                self.assertTrue(subcategory_model.objects.filter(
                    user=self.user,
                    category=category,
                ).exists())

            with self.subTest(record_type=record_type, kind="tag"):
                response = self.client.post(self.taxonomy_url(record_type), {
                    "kind": "tag",
                    "name": f"{record_type} tag",
                    "category_slug": category.slug,
                })
                self.assertEqual(response.status_code, 200)
                self.assertTrue(tag_model.objects.filter(user=self.user).exists())

    def test_cannot_create_taxonomy_in_another_users_workspace(self):
        response = self.client.post(
            self.taxonomy_url("article", self.other_user),
            {"kind": "category", "name": "Forbidden"},
        )

        self.assertEqual(response.status_code, 404)
        self.assertFalse(ArticleCategory.objects.filter(name="Forbidden").exists())

    def test_cannot_create_subcategory_under_another_users_category(self):
        category = ArticleCategory.objects.create(
            user=self.other_user,
            name="Other user's category",
        )

        response = self.client.post(self.taxonomy_url("article"), {
            "kind": "subcategory",
            "name": "Forbidden child",
            "category_slug": category.slug,
        })

        self.assertEqual(response.status_code, 404)
        self.assertFalse(
            ArticleSubcategory.objects.filter(name="Forbidden child").exists()
        )

    def test_uncategorized_cannot_have_subcategories_or_be_deleted(self):
        default_category = ArticleCategory.objects.get(
            user=self.user,
            slug="uncategorized",
        )

        create_response = self.client.post(self.taxonomy_url("article"), {
            "kind": "subcategory",
            "name": "Forbidden child",
            "category_slug": default_category.slug,
        })
        delete_response = self.client.post(self.taxonomy_delete_url("article"), {
            "kind": "category",
            "slug": default_category.slug,
        })

        self.assertEqual(create_response.status_code, 400)
        self.assertEqual(delete_response.status_code, 400)
        self.assertTrue(
            ArticleCategory.objects.filter(pk=default_category.pk).exists()
        )

    def test_deleting_subcategory_keeps_posts_in_parent_category(self):
        category = ArticleCategory.objects.create(user=self.user, name="Parent")
        subcategory = ArticleSubcategory.objects.create(
            user=self.user,
            category=category,
            name="Child",
        )
        article = Article.objects.create(
            user=self.user,
            category=category,
            subcategory=subcategory,
            title="Categorized article",
            content="Body",
        )

        response = self.client.post(self.taxonomy_delete_url("article"), {
            "kind": "subcategory",
            "slug": subcategory.slug,
        })

        article.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(article.category, category)
        self.assertIsNone(article.subcategory)
        self.assertFalse(
            ArticleSubcategory.objects.filter(pk=subcategory.pk).exists()
        )

    def test_deleting_category_moves_posts_to_uncategorized(self):
        category = ArticleCategory.objects.create(user=self.user, name="Temporary")
        subcategory = ArticleSubcategory.objects.create(
            user=self.user,
            category=category,
            name="Temporary child",
        )
        article = Article.objects.create(
            user=self.user,
            category=category,
            subcategory=subcategory,
            title="Article to move",
            content="Body",
        )

        response = self.client.post(self.taxonomy_delete_url("article"), {
            "kind": "category",
            "slug": category.slug,
        })

        article.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(article.category.slug, "uncategorized")
        self.assertEqual(article.category.user, self.user)
        self.assertIsNone(article.subcategory)
        self.assertFalse(ArticleCategory.objects.filter(pk=category.pk).exists())

    def test_deleting_tag_detaches_it_from_posts(self):
        category = ArticleCategory.objects.create(user=self.user, name="Tagged")
        tag = ArticleTag.objects.create(user=self.user, category=category, name="Temporary tag")
        article = Article.objects.create(
            user=self.user,
            category=category,
            title="Tagged article",
            content="Body",
        )
        article.tags.add(tag)

        response = self.client.post(self.taxonomy_delete_url("article"), {
            "kind": "tag",
            "slug": tag.slug,
            "category_slug": category.slug,
        })

        self.assertEqual(response.status_code, 200)
        self.assertFalse(ArticleTag.objects.filter(pk=tag.pk).exists())
        self.assertFalse(article.tags.exists())

    def test_tag_deletion_returns_to_category_for_each_record_type(self):
        index_routes = {
            record_type: models_for_type[0]._meta.model_name + "_index"
            for record_type, models_for_type in TAXONOMY_MODELS.items()
        }
        index_routes["article"] = "index"

        for record_type, models_for_type in TAXONOMY_MODELS.items():
            tag_model = models_for_type[3]
            category = models_for_type[1].objects.get(user=self.user, slug="uncategorized")
            tag = tag_model.objects.create(
                user=self.user,
                name=f"{record_type} redirect tag",
                category=category,
            )

            with self.subTest(record_type=record_type):
                response = self.client.post(
                    self.taxonomy_delete_url(record_type),
                    {"kind": "tag", "slug": tag.slug, "category_slug": category.slug},
                )

                self.assertEqual(response.status_code, 200)
                self.assertEqual(
                    response.json()["redirect_url"],
                    workspace_reverse(f"{record_type}_category", self.user, [category.slug]),
                )

    def test_cannot_delete_another_users_taxonomy(self):
        category = ArticleCategory.objects.create(
            user=self.other_user,
            name="Other private category",
        )

        response = self.client.post(self.taxonomy_delete_url("article"), {
            "kind": "category",
            "slug": category.slug,
        })

        self.assertEqual(response.status_code, 404)
        self.assertTrue(ArticleCategory.objects.filter(pk=category.pk).exists())


class LegacyDataRecoveryTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="legacy-owner",
            password="test-password",
        )
        self.category = ArticleCategory.objects.create(name="Legacy category")
        self.article = Article.objects.create(
            title="Legacy article",
            content="Still present",
            category=self.category,
        )

    def test_dry_run_does_not_change_legacy_rows(self):
        output = StringIO()

        call_command(
            "assign_legacy_data",
            username=self.user.username,
            stdout=output,
        )

        self.article.refresh_from_db()
        self.assertIsNone(self.article.user)
        self.assertIn("Dry run only", output.getvalue())

    def test_apply_assigns_legacy_rows_to_requested_user(self):
        call_command(
            "assign_legacy_data",
            username=self.user.username,
            apply=True,
            stdout=StringIO(),
        )

        self.article.refresh_from_db()
        self.category.refresh_from_db()
        self.assertEqual(self.article.user, self.user)
        self.assertEqual(self.category.user, self.user)

    def test_apply_merges_duplicate_legacy_uncategorized_safely(self):
        owned_default = ArticleCategory.objects.create(
            user=self.user,
            name="Uncategorized",
            slug="uncategorized",
        )
        legacy_default = ArticleCategory.objects.create(
            name="Uncategorized",
            slug="uncategorized",
        )
        legacy_article = Article.objects.create(
            title="Legacy default article",
            content="Still present",
            category=legacy_default,
        )

        call_command(
            "assign_legacy_data",
            username=self.user.username,
            apply=True,
            stdout=StringIO(),
        )

        legacy_article.refresh_from_db()
        self.assertEqual(legacy_article.user, self.user)
        self.assertEqual(legacy_article.category, owned_default)
        self.assertIsNone(legacy_article.subcategory)
        self.assertFalse(
            ArticleCategory.objects.filter(pk=legacy_default.pk).exists()
        )


class ScopedTagTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="scope-owner")
        self.client.force_login(self.user)

    def test_category_and_subcategory_tags_are_independent_for_all_types(self):
        for record_type, (_, Category, Subcategory, Tag) in TAXONOMY_MODELS.items():
            with self.subTest(record_type=record_type):
                category = Category.objects.create(user=self.user, name="Work")
                subcategory = Subcategory.objects.create(user=self.user, category=category, name="Planning")
                endpoint = workspace_reverse("taxonomy_create", self.user, [record_type])
                category_data = {"kind": "tag", "name": "Priority", "category_slug": category.slug}
                first = self.client.post(endpoint, category_data)
                second = self.client.post(endpoint, {**category_data, "subcategory_slug": subcategory.slug})
                self.assertEqual(first.status_code, 200)
                self.assertEqual(second.status_code, 200)
                self.assertNotEqual(first.json()["id"], second.json()["id"])
                self.assertEqual(self.client.post(endpoint, category_data).json()["id"], first.json()["id"])
                category_tag = Tag.objects.get(pk=first.json()["id"])
                subcategory_tag = Tag.objects.get(pk=second.json()["id"])
                self.assertIsNone(category_tag.subcategory)
                self.assertEqual(subcategory_tag.subcategory, subcategory)
                for route, args, expected in [
                    (f"{record_type}_category", [category.slug], category_tag),
                    (f"{record_type}_subcategory", [category.slug, subcategory.slug], subcategory_tag),
                    (f"{record_type}_tag", [subcategory_tag.slug], subcategory_tag),
                ]:
                    response = self.client.get(workspace_reverse(route, self.user, args))
                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(list(response.context["article_tags"]), [expected])
                    self.assertContains(response, 'data-category-slug="work"')
                index = "index" if record_type == "article" else f"{record_type}_index"
                self.assertNotContains(self.client.get(workspace_reverse(index, self.user)), 'class="tags"')
                deleted = self.client.post(workspace_reverse("taxonomy_delete", self.user, [record_type]), {
                    "kind": "tag", "slug": subcategory_tag.slug,
                    "category_slug": category.slug, "subcategory_slug": subcategory.slug,
                })
                self.assertEqual(deleted.status_code, 200)
                self.assertEqual(deleted.json()["redirect_url"], workspace_reverse(f"{record_type}_subcategory", self.user, [category.slug, subcategory.slug]))
                self.assertTrue(Tag.objects.filter(pk=category_tag.pk).exists())

    def test_tags_require_a_scope_and_cannot_use_another_users_scope(self):
        endpoint = workspace_reverse("taxonomy_create", self.user, ["article"])
        self.assertEqual(self.client.post(endpoint, {"kind": "tag", "name": "Missing"}).status_code, 400)
        other = User.objects.create_user(username="scope-other")
        category = ArticleCategory.objects.create(user=other, name="Private")
        self.assertEqual(self.client.post(endpoint, {"kind": "tag", "name": "Private", "category_slug": category.slug}).status_code, 404)

    def test_rejects_tags_from_other_scopes_when_saving_or_deleting(self):
        category = ArticleCategory.objects.create(user=self.user, name="Work")
        other = ArticleCategory.objects.create(user=self.user, name="Personal")
        subcategory = ArticleSubcategory.objects.create(user=self.user, category=category, name="Planning")
        tag = ArticleTag.objects.create(user=self.user, category=category, subcategory=subcategory, name="Priority")
        for selected, sub in [(other, None), (category, None)]:
            form = ArticleForm(user=self.user, data={"title": "Invalid", "content": "Body", "category": selected.pk, "subcategory": sub, "tags": [tag.pk]})
            self.assertFalse(form.is_valid())
            self.assertIn("tags", form.errors)
        result = self.client.post(workspace_reverse("taxonomy_delete", self.user, ["article"]), {"kind": "tag", "slug": tag.slug, "category_slug": other.slug})
        self.assertEqual(result.status_code, 404)
        self.assertTrue(ArticleTag.objects.filter(pk=tag.pk).exists())

    def test_new_tags_use_selected_subcategory_and_edit_clears_old_tags(self):
        category = ArticleCategory.objects.create(user=self.user, name="Work")
        subcategory = ArticleSubcategory.objects.create(user=self.user, category=category, name="Planning")
        data = {"title": "Tagged", "content": "Body", "category": category.pk, "subcategory": subcategory.pk, "new_tags": "Priority"}
        form = ArticleForm(user=self.user, data=data)
        self.assertTrue(form.is_valid(), form.errors)
        form.instance.user = self.user
        record = form.save()
        tag = record.tags.get()
        self.assertEqual(tag.category, category)
        self.assertEqual(tag.subcategory, subcategory)
        form = ArticleForm(user=self.user, instance=record, data={**data, "subcategory": "", "new_tags": ""})
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        self.assertFalse(record.tags.exists())
        self.assertTrue(ArticleTag.objects.filter(pk=tag.pk).exists())

    def test_scoped_tag_page_only_includes_records_assigned_to_tag(self):
        category = ArticleCategory.objects.create(user=self.user, name="Work")
        tag = ArticleTag.objects.create(user=self.user, category=category, name="Priority")
        first = Article.objects.create(user=self.user, category=category, title="Tagged", content="Body")
        second = Article.objects.create(user=self.user, category=category, title="Other", content="Body")
        other_category = ArticleCategory.objects.create(user=self.user, name="Personal")
        Article.objects.create(user=self.user, category=other_category, title="Outside", content="Body")
        first.tags.add(tag)
        response = self.client.get(workspace_reverse("article_tag", self.user, [tag.slug]))
        self.assertEqual(list(response.context["page_obj"]), [first])


class ScopedTagMigrationTests(TransactionTestCase):
    def test_preserves_shared_assignments_and_places_unused_tags_in_uncategorized(self):
        executor = MigrationExecutor(connection)
        before = [("core", "0005_recorddraft")]
        after = [("core", "0006_scope_tags")]
        executor.migrate(before)
        try:
            old = executor.loader.project_state(before).apps
            user = old.get_model("core", "User").objects.create(username="legacy-tags")
            for prefix in ("Article", "Journal", "Note", "CentralPoint", "Strategy", "Decision", "Goal"):
                Category = old.get_model("core", prefix + "Category")
                Subcategory = old.get_model("core", prefix + "Subcategory")
                Record = old.get_model("core", prefix)
                Tag = old.get_model("core", prefix + "Tag")
                category = Category.objects.create(user_id=user.pk, name="Work", slug="work")
                other = Category.objects.create(user_id=user.pk, name="Personal", slug="personal")
                subcategory = Subcategory.objects.create(user_id=user.pk, category=category, name="Planning", slug="planning")
                tag = Tag.objects.create(user_id=user.pk, name="Shared", slug="shared")
                Tag.objects.create(user_id=user.pk, name="Unused", slug="unused")
                for index, (cat, sub) in enumerate([(category, None), (category, subcategory), (other, None)]):
                    # Historical records have type-specific required text fields.
                    fields = {field.name: "Body" for field in Record._meta.fields if field.get_internal_type() in ("TextField", "CKEditor5Field")}
                    fields.update({field.name: date(2026, 11, 13) for field in Record._meta.fields if field.get_internal_type() == "DateField" and not field.null})
                    record = Record.objects.create(user_id=user.pk, category=cat, subcategory=sub, title=f"Legacy {index}", slug=f"legacy-{index}", **fields)
                    record.tags.add(tag)
            executor = MigrationExecutor(connection)
            executor.migrate(after)
            new = executor.loader.project_state(after).apps
            for prefix in ("Article", "Journal", "Note", "CentralPoint", "Strategy", "Decision", "Goal"):
                Record = new.get_model("core", prefix)
                Tag = new.get_model("core", prefix + "Tag")
                self.assertEqual(Tag.objects.filter(name="Shared").count(), 3)
                for record in Record.objects.filter(user_id=user.pk):
                    tag = record.tags.get()
                    self.assertEqual(tag.category_id, record.category_id)
                    self.assertEqual(tag.subcategory_id, record.subcategory_id)
                    self.assertEqual(tag.name, "Shared")
                unused = Tag.objects.get(name="Unused")
                self.assertEqual(unused.category.slug, "uncategorized")
                self.assertIsNone(unused.subcategory_id)
        finally:
            MigrationExecutor(connection).migrate([("core", "0008_preserve_posts_on_taxonomy_delete")])


class NestedSubcategoryTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="nested-owner")
        self.client.force_login(self.user)

    def hierarchy(self, record_type):
        _, Category, Subcategory, _ = TAXONOMY_MODELS[record_type]
        category = Category.objects.create(user=self.user, name="Work")
        parent = Subcategory.objects.create(user=self.user, category=category, name="Projects")
        child = Subcategory.objects.create(user=self.user, category=category, parent=parent, name="Planning")
        return category, parent, child

    def post_data(self, record_type, **values):
        from django import forms
        from .views import RECORD_FORMS
        form_class = RECORD_FORMS[record_type][1]
        data = {name: ("2026-11-14" if isinstance(field, forms.DateField) else "Body")
                for name, field in form_class(user=self.user).fields.items()
                if field.required and name not in {"category", "subcategory", "tags"}}
        return {**data, "title": "Nested post", **values}

    def test_creates_two_levels_and_rejects_third_for_every_post_type(self):
        for record_type, (_, Category, Subcategory, _) in TAXONOMY_MODELS.items():
            with self.subTest(record_type=record_type):
                category, parent, child = self.hierarchy(record_type)
                endpoint = workspace_reverse("taxonomy_create", self.user, [record_type])
                data = {"kind":"subcategory", "category_slug":category.slug, "parent_slug":parent.slug, "name":"Second child"}
                response = self.client.post(endpoint, data)
                self.assertEqual(response.status_code, 200)
                created = Subcategory.objects.get(pk=response.json()["id"])
                self.assertEqual(created.parent, parent)
                self.assertEqual(self.client.post(endpoint,data).json()["id"], created.pk)
                rejected = self.client.post(endpoint,{**data,"parent_slug":child.slug,"name":"Too deep"})
                self.assertEqual(rejected.status_code,400)
                self.assertFalse(Subcategory.objects.filter(name="Too deep").exists())

    def test_forms_save_select_and_restore_child_tags_for_every_post_type(self):
        from .views import RECORD_FORMS
        for record_type, (Record, _, _, Tag) in TAXONOMY_MODELS.items():
            with self.subTest(record_type=record_type):
                category,parent,child = self.hierarchy(record_type)
                tag = Tag.objects.create(user=self.user,category=category,subcategory=child,name="Priority")
                form_class = RECORD_FORMS[record_type][1]
                form = form_class(user=self.user,data=self.post_data(record_type, category=category.pk,subcategory=parent.pk,child_subcategory=child.pk,tags=[tag.pk]))
                self.assertTrue(form.is_valid(),form.errors)
                form.instance.user = self.user
                record = form.save()
                self.assertEqual(record.subcategory,child)
                self.assertEqual(record.tags.get(),tag)
                edit = form_class(user=self.user,instance=record)
                self.assertEqual(edit.initial["subcategory"],parent.pk)
                self.assertEqual(edit.initial["child_subcategory"],child.pk)
                self.assertNotIn(child,edit.fields["subcategory"].queryset)
                self.assertIn(child,edit.fields["child_subcategory"].queryset)
                for route,args in [(f"{record_type}_subcategory",[category.slug,parent.slug]),(f"{record_type}_subcategory",[category.slug,child.slug]),(f"{record_type}_tag",[tag.slug])]:
                    response = self.client.get(workspace_reverse(route,self.user,args))
                    self.assertEqual(response.status_code,200)
                    self.assertEqual(list(response.context["page_obj"]),[record])
                    self.assertContains(response,f'<li data-subcategory-slug="{child.slug}"',count=1)
                single = self.client.get(workspace_reverse(f"{record_type}_single",self.user,[record.slug]))
                self.assertContains(single, 'aria-label="Subcategory: Projects"')
                self.assertContains(single, 'aria-label="Subcategory: Planning"')

    def test_form_can_create_entire_hierarchy_and_tags(self):
        form = ArticleForm(user=self.user,data={"title":"New tree","content":"Body","new_category":"Work","new_subcategory":"Projects","new_child_subcategory":"Planning","new_tags":"Priority"})
        self.assertTrue(form.is_valid(),form.errors)
        form.instance.user = self.user
        record = form.save()
        self.assertEqual(record.subcategory.name,"Planning")
        self.assertEqual(record.subcategory.parent.name,"Projects")
        self.assertEqual(record.tags.get().subcategory,record.subcategory)

    def test_rejects_wrong_parent_scope_and_tags_from_another_branch(self):
        category,parent,child = self.hierarchy("article")
        sibling = ArticleSubcategory.objects.create(user=self.user,category=category,name="Other")
        base = {"title":"Invalid","content":"Body","category":category.pk,"subcategory":sibling.pk,"child_subcategory":child.pk}
        form = ArticleForm(user=self.user,data=base)
        self.assertFalse(form.is_valid())
        self.assertIn("child_subcategory",form.errors)
        tag = ArticleTag.objects.create(user=self.user,category=category,subcategory=sibling,name="Other branch only")
        form = ArticleForm(user=self.user,data={**base,"subcategory":parent.pk,"tags":[tag.pk]})
        self.assertFalse(form.is_valid())
        self.assertIn("tags",form.errors)
        form = ArticleForm(user=self.user,data={**base,"subcategory":"","child_subcategory":"","new_child_subcategory":"Missing parent"})
        self.assertFalse(form.is_valid())
        self.assertIn("new_child_subcategory",form.errors)

    def test_model_rejects_cycles_depth_and_cross_workspace_parents(self):
        from django.core.exceptions import ValidationError
        for record_type, (_, Category, Subcategory, _) in TAXONOMY_MODELS.items():
            with self.subTest(record_type=record_type):
                category,parent,child = self.hierarchy(record_type)
                with self.assertRaises(ValidationError):
                    Subcategory.objects.create(user=self.user,category=category,parent=child,name="Third")
                parent.parent = child
                with self.assertRaises(ValidationError):
                    parent.save()
                parent.parent = parent
                with self.assertRaises(ValidationError):
                    parent.save()
                other = Category.objects.create(user=self.user,name="Other")
                with self.assertRaises(ValidationError):
                    Subcategory.objects.create(user=self.user,category=other,parent=child,name="Wrong category")
                outsider = User.objects.create_user(username=f"outsider-{record_type}")
                with self.assertRaises(ValidationError):
                    Subcategory.objects.create(user=outsider,category=category,name="Wrong owner")

    def test_deleting_either_level_preserves_posts(self):
        for delete_parent in (False,True):
            with self.subTest(delete_parent=delete_parent):
                # Use a separate type per case so names remain independent.
                record_type = "article" if delete_parent else "note"
                Record,_,Subcategory,Tag = TAXONOMY_MODELS[record_type]
                category,parent,child = self.hierarchy(record_type)
                record = Record.objects.create(user=self.user,category=category,subcategory=child,title="Keep me",content="Body")
                tag = Tag.objects.create(user=self.user,category=category,subcategory=child,name="Temporary")
                record.tags.add(tag)
                response = self.client.post(workspace_reverse("taxonomy_delete",self.user,[record_type]),{"kind":"subcategory","slug":parent.slug if delete_parent else child.slug})
                self.assertEqual(response.status_code,200)
                record.refresh_from_db()
                self.assertEqual(record.category,category)
                self.assertEqual(record.subcategory,None if delete_parent else parent)
                self.assertFalse(record.tags.exists())
                self.assertFalse(Subcategory.objects.filter(pk=child.pk).exists())

    def test_draft_restores_both_levels(self):
        category,parent,child = self.hierarchy("article")
        RecordDraft.objects.create(user=self.user,record_type="article",data={"category":[str(category.pk)],"subcategory":[str(parent.pk)],"child_subcategory":[str(child.pk)]})
        response = self.client.get(workspace_reverse("article_create",self.user))
        form = response.context["form"]
        self.assertEqual(str(form["subcategory"].value()),str(parent.pk))
        self.assertEqual(str(form["child_subcategory"].value()),str(child.pk))


class CategoryTagSectionTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="category-tag-sections")
        self.client.force_login(self.user)

    def test_each_level_only_manages_its_own_tags_for_all_types(self):
        for record_type, (_, Category, Subcategory, Tag) in TAXONOMY_MODELS.items():
            with self.subTest(record_type=record_type):
                category = Category.objects.create(user=self.user, name="Work")
                parent = Subcategory.objects.create(user=self.user, category=category, name="Projects")
                child = Subcategory.objects.create(user=self.user, category=category, parent=parent, name="Planning")
                scopes = [None, parent, child]
                tags = [Tag.objects.create(user=self.user, category=category, subcategory=scope,
                                           name=f"Level {level} marker")
                        for level, scope in enumerate(scopes, 1)]
                for scope, tag in zip(scopes, tags):
                    route = f"{record_type}_subcategory" if scope else f"{record_type}_category"
                    args = [category.slug, scope.slug] if scope else [category.slug]
                    for url in [workspace_reverse(route, self.user, args),
                                workspace_reverse(f"{record_type}_tag", self.user, [tag.slug])]:
                        response = self.client.get(url)
                        self.assertEqual(response.status_code, 200)
                        self.assertContains(response, tag.name)
                        for other_tag in tags:
                            if other_tag != tag:
                                self.assertNotContains(response, other_tag.name)
                        self.assertContains(response, f'data-subcategory-slug="{scope.slug if scope else ""}"')
                        self.assertEqual(list(response.context["article_tags"]), [tag])

    def test_empty_scopes_still_offer_tag_management_when_they_have_children(self):
        for record_type, (_, Category, Subcategory, _) in TAXONOMY_MODELS.items():
            with self.subTest(record_type=record_type):
                category = Category.objects.create(user=self.user, name="Work")
                parent = Subcategory.objects.create(user=self.user, category=category, name="Projects")
                child = Subcategory.objects.create(user=self.user, category=category, parent=parent, name="Planning")
                for scope in [None, parent, child]:
                    route = f"{record_type}_subcategory" if scope else f"{record_type}_category"
                    args = [category.slug, scope.slug] if scope else [category.slug]
                    response = self.client.get(workspace_reverse(route, self.user, args))
                    self.assertContains(response, '<ul class="tags"')
                    self.assertContains(response, 'No tags yet.')
                    self.assertContains(response, f'data-subcategory-slug="{scope.slug if scope else ""}"')


    def test_tag_changes_stay_within_each_of_the_three_scopes(self):
        for record_type, (_, Category, Subcategory, Tag) in TAXONOMY_MODELS.items():
            with self.subTest(record_type=record_type):
                category = Category.objects.create(user=self.user, name="Work")
                parent = Subcategory.objects.create(user=self.user, category=category, name="Projects")
                child = Subcategory.objects.create(user=self.user, category=category, parent=parent, name="Planning")
                create_url = workspace_reverse("taxonomy_create", self.user, [record_type])
                delete_url = workspace_reverse("taxonomy_delete", self.user, [record_type])
                tags = []
                for scope in [None, parent, child]:
                    data = {"kind": "tag", "name": "Priority", "category_slug": category.slug,
                            "subcategory_slug": scope.slug if scope else ""}
                    response = self.client.post(create_url, data)
                    self.assertEqual(response.status_code, 200)
                    tags.append(Tag.objects.get(pk=response.json()["id"]))
                for scope, tag in zip([None, parent, child], tags):
                    wrong_scope = child if scope != child else parent
                    response = self.client.post(delete_url, {
                        "kind": "tag", "slug": tag.slug, "category_slug": category.slug,
                        "subcategory_slug": wrong_scope.slug,
                    })
                    self.assertEqual(response.status_code, 404)
                    self.assertTrue(Tag.objects.filter(pk=tag.pk).exists())
                for scope, tag in zip([None, parent, child], tags):
                    response = self.client.post(delete_url, {
                        "kind": "tag", "slug": tag.slug, "category_slug": category.slug,
                        "subcategory_slug": scope.slug if scope else "",
                    })
                    self.assertEqual(response.status_code, 200)
                    self.assertFalse(Tag.objects.filter(pk=tag.pk).exists())


class ExplicitPostTagTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="explicit-tags")
        self.client.force_login(self.user)

    def hierarchy(self, record_type):
        _, Category, Subcategory, Tag = TAXONOMY_MODELS[record_type]
        category = Category.objects.create(user=self.user, name="Personal development")
        parent = Subcategory.objects.create(user=self.user, category=category, name="Time and place")
        child = Subcategory.objects.create(user=self.user, category=category, parent=parent, name="Space")
        tags = [Tag.objects.create(user=self.user, category=category, subcategory=scope, name=name)
                for scope, name in [(None, "time management"), (parent, "time&space"), (child, "space")]]
        return category, parent, child, tags

    def form_data(self, form_class, **values):
        from django import forms
        data = {name: ("2026-11-14" if isinstance(field, forms.DateField) else "Body")
                for name, field in form_class(user=self.user).fields.items()
                if field.required and name not in {"category", "subcategory", "tags"}}
        return {**data, "title": "Selected tags post", **values}

    def test_selects_saves_edits_and_displays_each_combination_of_levels_for_every_type(self):
        from html import unescape
        from .views import RECORD_FORMS
        for record_type in TAXONOMY_MODELS:
            with self.subTest(record_type=record_type):
                category, parent, child, tags = self.hierarchy(record_type)
                form_class = RECORD_FORMS[record_type][1]
                record = None
                # No tags, any single level, any pair, and all three levels are independent choices.
                for mask in range(8):
                    selected = [tag for index, tag in enumerate(tags) if mask & (1 << index)]
                    form = form_class(user=self.user, instance=record, data=self.form_data(
                        form_class, category=category.pk, subcategory=parent.pk,
                        child_subcategory=child.pk, tags=[tag.pk for tag in selected],
                    ))
                    self.assertTrue(form.is_valid(), form.errors)
                    form.instance.user = self.user
                    record = form.save()
                    self.assertCountEqual(record.tags.all(), selected)
                    edit = form_class(user=self.user, instance=record)
                    self.assertCountEqual(edit["tags"].value(), [tag.pk for tag in selected])
                    # Initial checkbox values retain tags from all selected levels.
                    rendered = str(edit["tags"])
                    self.assertEqual(rendered.count(' checked'), len(selected))
                    response = self.client.get(workspace_reverse(f"{record_type}_single", self.user, [record.slug]))
                    markup = unescape(response.content.decode()).split('<nav class="post-taxonomy"', 1)[1].split('</nav>', 1)[0]
                    self.assertEqual(markup.count('class="post-taxonomy-tag"'), len(selected))
                    for tag in tags:
                        href = workspace_reverse(f"{record_type}_tag", self.user, [tag.slug])
                        self.assertEqual(f'href="{href}"' in markup, tag in selected)
                # Unassigned scope tags never appear on preview cards either.
                record.tags.set([tags[0], tags[2]])
                index_route = "index" if record_type == "article" else f"{record_type}_index"
                for url in [workspace_reverse(index_route, self.user),
                            workspace_reverse(f"{record_type}_category", self.user, [category.slug]),
                            workspace_reverse(f"{record_type}_subcategory", self.user, [category.slug, parent.slug]),
                            workspace_reverse(f"{record_type}_subcategory", self.user, [category.slug, child.slug])]:
                    response = self.client.get(url)
                    markup = response.content.decode().split('<nav class="post-taxonomy"', 1)[1].split('</nav>', 1)[0]
                    self.assertEqual(markup.count('class="post-taxonomy-tag"'), 2)
                    self.assertNotIn(workspace_reverse(f"{record_type}_tag", self.user, [tags[1].slug]), markup)
                for tag in tags:
                    response = self.client.get(workspace_reverse(f"{record_type}_tag", self.user, [tag.slug]))
                    expected = [] if tag == tags[1] else [record]
                    self.assertEqual(list(response.context["page_obj"]), expected)

    def test_only_tags_on_selected_path_are_allowed_for_all_types(self):
        from .views import RECORD_FORMS
        for record_type, (_, Category, Subcategory, Tag) in TAXONOMY_MODELS.items():
            with self.subTest(record_type=record_type):
                category, parent, child, tags = self.hierarchy(record_type)
                sibling = Subcategory.objects.create(user=self.user, category=category, parent=parent, name="Sibling")
                other = Category.objects.create(user=self.user, name="Unrelated")
                outsider = User.objects.create_user(username=f"outsider-{record_type}")
                invalid_tags = [Tag.objects.create(user=self.user, category=category, subcategory=sibling, name="Sibling tag"),
                                Tag.objects.create(user=self.user, category=other, name="Other category tag"),
                                Tag.objects.create(user=outsider, category=other, name="Private tag")]
                form_class = RECORD_FORMS[record_type][1]
                base = self.form_data(form_class, category=category.pk, subcategory=parent.pk, child_subcategory=child.pk)
                for tag in invalid_tags:
                    form = form_class(user=self.user, data={**base, "tags": [tag.pk]})
                    self.assertFalse(form.is_valid())
                    self.assertIn("tags", form.errors)
                # Moving up the path disallows deeper tags but keeps selections at remaining levels.
                form = form_class(user=self.user, data={**base, "child_subcategory": "", "tags": [tags[2].pk]})
                self.assertFalse(form.is_valid())
                form = form_class(user=self.user, data={**base, "child_subcategory": "", "tags": [tags[0].pk, tags[1].pk]})
                self.assertTrue(form.is_valid(), form.errors)

    def test_new_subcategories_allow_existing_parent_tags(self):
        category, parent, child, tags = self.hierarchy("article")
        for values, selected in [({"new_subcategory": "New branch"}, [tags[0]]),
                                 ({"subcategory": parent.pk, "new_child_subcategory": "New leaf"}, tags[:2])]:
            form = ArticleForm(user=self.user, data={"title": f"New path {len(selected)}", "content": "Body",
                "category": category.pk, "tags": [tag.pk for tag in selected], **values})
            self.assertTrue(form.is_valid(), form.errors)
            form.instance.user = self.user
            record = form.save()
            self.assertCountEqual(record.tags.all(), selected)

    def test_tag_choices_identify_their_category_level(self):
        category, parent, child, tags = self.hierarchy("article")
        from html import unescape
        markup = unescape(str(ArticleForm(user=self.user)["tags"]))
        self.assertIn("Personal development: time management", markup)
        self.assertIn("Personal development / Time and place: time&space", markup)
        self.assertIn("Personal development / Time and place / Space: space", markup)

    def test_selected_tags_do_not_add_queries_per_post(self):
        from .views import records_for_user
        category, parent, child, tags = self.hierarchy("article")
        for number in range(6):
            record = Article.objects.create(user=self.user, category=category, subcategory=child,
                                            title=f"Post {number}", content="Body")
            record.tags.set(tags)
        with self.assertNumQueries(2):
            for record in records_for_user(Article, self.user):
                self.assertEqual(len(record.tags.all()), 3)
                for tag in record.tags.all():
                    self.assertEqual(tag.category.name, category.name)
                    if tag.subcategory:
                        self.assertTrue(tag.subcategory.name)


class PerLevelTagCreationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="level-tag-creator")
        self.client.force_login(self.user)

    def test_creates_tags_at_each_level_with_a_new_hierarchy_for_all_types(self):
        from .views import RECORD_FORMS
        for record_type, (_, Category, Subcategory, Tag) in TAXONOMY_MODELS.items():
            with self.subTest(record_type=record_type):
                form_class = RECORD_FORMS[record_type][1]
                data = ExplicitPostTagTests.form_data(self, form_class,
                    new_category="Personal development", new_subcategory="Time and place",
                    new_child_subcategory="Space", new_category_tags="Shared, habits",
                    new_subcategory_tags="Shared, time&space", new_child_tags="Shared, space")
                response = self.client.post(workspace_reverse(f"{record_type}_create", self.user), data)
                self.assertEqual(response.status_code, 302)
                record = TAXONOMY_MODELS[record_type][0].objects.get(user=self.user)
                self.assertEqual(record.tags.count(), 6)
                self.assertCountEqual(record.tags.filter(subcategory=None).values_list("name", flat=True), ["Shared", "habits"])
                self.assertCountEqual(record.tags.filter(subcategory=record.subcategory.parent).values_list("name", flat=True), ["Shared", "time&space"])
                self.assertCountEqual(record.tags.filter(subcategory=record.subcategory).values_list("name", flat=True), ["Shared", "space"])
                self.assertEqual(Tag.objects.filter(name="Shared", user=self.user).count(), 3)
                edit = self.client.get(workspace_reverse(f"{record_type}_edit", self.user, [record.slug]))
                self.assertContains(edit, 'data-tag-level="category"', count=1)
                self.assertContains(edit, 'data-tag-level="subcategory"', count=1)
                self.assertContains(edit, 'data-tag-level="child"', count=1)
                self.assertContains(edit, 'name="new_category_tags"', count=1)
                self.assertContains(edit, 'name="new_subcategory_tags"', count=1)
                self.assertContains(edit, 'name="new_child_tags"', count=1)

    def test_edit_reuses_tags_in_each_scope_and_only_assigns_explicit_choices(self):
        from .views import RECORD_FORMS
        for record_type, (Record, _, _, Tag) in TAXONOMY_MODELS.items():
            with self.subTest(record_type=record_type):
                category, parent, child, tags = ExplicitPostTagTests.hierarchy(self, record_type)
                form_class = RECORD_FORMS[record_type][1]
                data = ExplicitPostTagTests.form_data(self, form_class, category=category.pk,
                    subcategory=parent.pk, child_subcategory=child.pk,
                    new_category_tags="TIME MANAGEMENT, time management", new_subcategory_tags="time&space",
                    new_child_tags="space")
                form = form_class(user=self.user, data=data)
                self.assertTrue(form.is_valid(), form.errors)
                form.instance.user = self.user
                record = form.save()
                self.assertCountEqual(record.tags.all(), tags)
                self.assertEqual(Tag.objects.filter(user=self.user).count(), 3)
                data.update(tags=[tags[0].pk], new_category_tags="", new_subcategory_tags="New middle", new_child_tags="New leaf")
                response = self.client.post(workspace_reverse(f"{record_type}_edit", self.user, [record.slug]), data)
                self.assertEqual(response.status_code, 302)
                record.refresh_from_db()
                self.assertCountEqual(record.tags.values_list("name", flat=True), [tags[0].name, "New middle", "New leaf"])
                self.assertTrue(Tag.objects.filter(pk=tags[1].pk).exists())
                self.assertFalse(record.tags.filter(pk=tags[1].pk).exists())

    def test_missing_scope_and_overlong_names_are_rejected_without_creating_tags(self):
        category = ArticleCategory.objects.create(user=self.user, name="Work")
        for field, value in [("new_subcategory_tags", "No parent"), ("new_child_tags", "No child"),
                             ("new_category_tags", "x" * 256)]:
            form = ArticleForm(user=self.user, data={"title": "Invalid", "content": "Body",
                                                    "category": category.pk, field: value})
            self.assertFalse(form.is_valid())
            self.assertIn(field, form.errors)
            self.assertFalse(ArticleTag.objects.filter(user=self.user).exists())

    def test_older_drafts_show_pending_tags_in_their_matching_level(self):
        category = ArticleCategory.objects.create(user=self.user, name="Work")
        parent = ArticleSubcategory.objects.create(user=self.user, category=category, name="Projects")
        child = ArticleSubcategory.objects.create(user=self.user, category=category, parent=parent, name="Planning")
        for scope, field in [(None, "new_category_tags"), (parent, "new_subcategory_tags"), (child, "new_child_tags")]:
            form = ArticleForm(user=self.user, initial={"category": category.pk,
                "subcategory": scope.pk if scope else None, "new_tags": "Older pending tag"})
            self.assertEqual(form[field].value(), "Older pending tag")
            self.assertEqual(form["new_tags"].value(), "")

    def test_validation_errors_and_drafts_keep_per_level_tag_names(self):
        category = ArticleCategory.objects.create(user=self.user, name="Work")
        parent = ArticleSubcategory.objects.create(user=self.user, category=category, name="Projects")
        child = ArticleSubcategory.objects.create(user=self.user, category=category, parent=parent, name="Planning")
        data = {"category": str(category.pk), "subcategory": str(parent.pk), "child_subcategory": str(child.pk),
                "new_category_tags": "Root pending", "new_subcategory_tags": "Parent pending", "new_child_tags": "Child pending"}
        response = self.client.post(workspace_reverse("article_create", self.user), data)
        self.assertEqual(response.status_code, 200)
        for field in ["new_category_tags", "new_subcategory_tags", "new_child_tags"]:
            self.assertEqual(response.context["form"][field].value(), data[field])
        saved = self.client.post(workspace_reverse("record_autosave", self.user, ["article"]), data)
        self.assertEqual(saved.status_code, 200)
        response = self.client.get(workspace_reverse("article_create", self.user))
        for field in ["new_category_tags", "new_subcategory_tags", "new_child_tags"]:
            self.assertEqual(response.context["form"][field].value(), data[field])


class TaxonomyPostPreservationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="preservation-owner")
        self.client.force_login(self.user)

    def record(self, Record, title, category, subcategory=None):
        fields = {field.name: "Original body" for field in Record._meta.fields
                  if field.get_internal_type() in ("TextField", "CKEditor5Field")}
        fields.update({field.name: date(2026,11,13) for field in Record._meta.fields
                       if field.get_internal_type() == "DateField" and not field.null})
        return Record.objects.create(user=self.user,title=title,category=category,subcategory=subcategory,**fields)

    def delete(self, mode, record_type, kind, item):
        if mode == "model":
            item.delete()
        elif mode == "bulk":
            type(item).objects.filter(pk=item.pk).delete()
        else:
            data = {"kind":kind,"slug":item.slug}
            if kind == "tag":
                data.update(category_slug=item.category.slug,subcategory_slug=item.subcategory.slug if item.subcategory_id else "")
            response = self.client.post(workspace_reverse("taxonomy_delete",self.user,[record_type]),data)
            self.assertEqual(response.status_code,200)

    def test_entire_deletion_ladder_preserves_posts_for_all_types_and_deletion_paths(self):
        for record_type, (Record,Category,Subcategory,Tag) in TAXONOMY_MODELS.items():
            for mode in ("model","bulk","sidebar"):
                with self.subTest(record_type=record_type,mode=mode):
                    category = Category.objects.create(user=self.user,name=f"Work {mode}")
                    parent = Subcategory.objects.create(user=self.user,category=category,name=f"Projects {mode}")
                    child = Subcategory.objects.create(user=self.user,category=category,parent=parent,name=f"Planning {mode}")
                    unrelated_category = Category.objects.create(user=self.user,name=f"Unrelated {mode}")
                    category_post = self.record(Record,f"Category {mode}",category)
                    parent_post = self.record(Record,f"Parent {mode}",category,parent)
                    child_post = self.record(Record,f"Child {mode}",category,child)
                    unrelated_post = self.record(Record,f"Unrelated {mode}",unrelated_category)
                    category_tag = Tag.objects.create(user=self.user,category=category,name=f"Category tag {mode}")
                    parent_tag = Tag.objects.create(user=self.user,category=category,subcategory=parent,name=f"Parent tag {mode}")
                    child_tag = Tag.objects.create(user=self.user,category=category,subcategory=child,name=f"Child tag {mode}")
                    extra_tag = Tag.objects.create(user=self.user,category=category,subcategory=child,name=f"Extra tag {mode}")
                    category_post.tags.add(category_tag)
                    parent_post.tags.add(parent_tag)
                    child_post.tags.add(child_tag,extra_tag)
                    records = [category_post,parent_post,child_post,unrelated_post]
                    preserved_fields = [field.attname for field in Record._meta.fields if field.name not in {"category","subcategory"}]
                    snapshots = {r.pk: {field:getattr(r,field) for field in preserved_fields} for r in records}
                    def unchanged():
                        for record in records:
                            record.refresh_from_db()
                            self.assertEqual({field:getattr(record,field) for field in preserved_fields},snapshots[record.pk])
                        self.assertEqual(unrelated_post.category,unrelated_category)
                    self.delete(mode,record_type,"tag",child_tag)
                    unchanged()
                    self.assertEqual(child_post.subcategory,child)
                    self.assertEqual(child_post.category,category)
                    self.assertEqual(list(child_post.tags.all()),[extra_tag])
                    self.delete(mode,record_type,"subcategory",child)
                    unchanged()
                    self.assertEqual(child_post.subcategory,parent)
                    self.assertEqual(parent_post.subcategory,parent)
                    self.assertFalse(child_post.tags.exists())
                    self.assertTrue(parent_post.tags.filter(pk=parent_tag.pk).exists())
                    self.delete(mode,record_type,"subcategory",parent)
                    unchanged()
                    for record in (category_post,parent_post,child_post):
                        self.assertEqual(record.category,category)
                        self.assertIsNone(record.subcategory)
                    self.assertTrue(category_post.tags.filter(pk=category_tag.pk).exists())
                    self.delete(mode,record_type,"category",category)
                    unchanged()
                    for record in (category_post,parent_post,child_post):
                        self.assertEqual(record.category.slug,"uncategorized")
                        self.assertEqual(record.category.user,self.user)
                        self.assertIsNone(record.subcategory)
                        self.assertFalse(record.tags.exists())

    def test_deleting_first_level_subcategory_with_children_keeps_all_posts_in_category(self):
        for record_type,(Record,Category,Subcategory,_) in TAXONOMY_MODELS.items():
            with self.subTest(record_type=record_type):
                category = Category.objects.create(user=self.user,name="Work")
                parent = Subcategory.objects.create(user=self.user,category=category,name="Projects")
                child = Subcategory.objects.create(user=self.user,category=category,parent=parent,name="Planning")
                first = self.record(Record,"Parent post",category,parent)
                second = self.record(Record,"Child post",category,child)
                Subcategory.objects.filter(pk__in=[parent.pk,child.pk]).delete()
                for record in (first,second):
                    record.refresh_from_db()
                    self.assertEqual(record.category,category)
                    self.assertIsNone(record.subcategory)

    def test_bulk_category_deletion_uses_original_queryset_membership(self):
        first = ArticleCategory.objects.create(user=self.user,name="First")
        second = ArticleCategory.objects.create(user=self.user,name="Second")
        posts = [self.record(Article,"Bulk first",first),self.record(Article,"Bulk second",second)]
        ArticleCategory.objects.filter(articles__title__startswith="Bulk").delete()
        for post in posts:
            post.refresh_from_db()
            self.assertEqual(post.category.slug,"uncategorized")
            self.assertIsNone(post.subcategory)
        self.assertFalse(ArticleCategory.objects.filter(pk__in=[first.pk,second.pk]).exists())

    def test_admin_deletion_preview_never_collects_posts_and_does_not_change_data(self):
        from django.contrib.admin.utils import NestedObjects
        category = ArticleCategory.objects.create(user=self.user,name="Work")
        subcategory = ArticleSubcategory.objects.create(user=self.user,category=category,name="Projects")
        post = self.record(Article,"Keep in preview",category,subcategory)
        collector = NestedObjects(using="default")
        collector.collect([category])
        self.assertNotIn(Article,collector.data)
        post.refresh_from_db()
        self.assertEqual(post.category,category)
        self.assertEqual(post.subcategory,subcategory)

    def test_saved_draft_follows_the_same_deletion_ladder(self):
        category = ArticleCategory.objects.create(user=self.user,name="Work")
        parent = ArticleSubcategory.objects.create(user=self.user,category=category,name="Projects")
        child = ArticleSubcategory.objects.create(user=self.user,category=category,parent=parent,name="Planning")
        tag = ArticleTag.objects.create(user=self.user,category=category,subcategory=child,name="Priority")
        draft = RecordDraft.objects.create(user=self.user,record_type="article",data={
            "title":["Keep this draft"],"content":["Keep the original body"],
            "category":[str(category.pk)],"subcategory":[str(parent.pk)],
            "child_subcategory":[str(child.pk)],"tags":[str(tag.pk)],
        })
        tag.delete()
        draft.refresh_from_db()
        self.assertEqual(draft.data["tags"],[])
        self.assertEqual(draft.data["child_subcategory"],[str(child.pk)])
        child.delete()
        draft.refresh_from_db()
        self.assertEqual(draft.data["subcategory"],[str(parent.pk)])
        self.assertEqual(draft.data["child_subcategory"],[""])
        parent.delete()
        draft.refresh_from_db()
        self.assertEqual(draft.data["subcategory"],[""])
        category.delete()
        draft.refresh_from_db()
        self.assertEqual(draft.data["category"],[str(ArticleCategory.objects.get(user=self.user,slug="uncategorized").pk)])
        self.assertEqual(draft.data["title"],["Keep this draft"])
        self.assertEqual(draft.data["content"],["Keep the original body"])

    def test_account_deletion_still_deletes_its_own_data(self):
        category = ArticleCategory.objects.create(user=self.user,name="Work")
        self.record(Article,"Account post",category)
        user_id = self.user.pk
        self.user.delete()
        self.assertFalse(Article.objects.filter(user_id=user_id).exists())
        self.assertFalse(ArticleCategory.objects.filter(user_id=user_id).exists())

    def test_uncategorized_is_protected_outside_the_sidebar(self):
        from django.db.models.deletion import ProtectedError
        category = ArticleCategory.objects.get(user=self.user,slug="uncategorized")
        with self.assertRaises(ProtectedError), transaction.atomic():
            ArticleCategory.objects.filter(pk=category.pk).delete()
        self.assertTrue(ArticleCategory.objects.filter(pk=category.pk).exists())

    def test_failed_deletion_rolls_back_post_reassignment(self):
        from django.db.models.signals import pre_delete
        category = ArticleCategory.objects.create(user=self.user,name="Work")
        post = self.record(Article,"Preserved after error",category)
        def fail_deletion(**kwargs):
            raise RuntimeError("Delete failed")
        pre_delete.connect(fail_deletion,sender=ArticleCategory,weak=False)
        try:
            with self.assertRaises(RuntimeError), transaction.atomic():
                category.delete()
        finally:
            pre_delete.disconnect(fail_deletion,sender=ArticleCategory)
        post.refresh_from_db()
        self.assertEqual(post.category,category)
        self.assertTrue(ArticleCategory.objects.filter(pk=category.pk).exists())


class AdminUserManagementTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_superuser(username="site-admin",email="admin@example.test",password="AdminTestPassw0rd!")
        cls.target = User.objects.create_user(username="managed-user",email="managed@example.test",password="OriginalTestPassw0rd!")
        cls.staff = User.objects.create_user(username="staff-without-permissions",is_staff=True)

    def setUp(self):
        self.client.force_login(self.admin)

    def test_custom_admin_shows_users_and_groups_and_management_pages(self):
        response = self.client.get(reverse("knowledge_admin:index"))
        self.assertContains(response,"Users and permissions")
        self.assertContains(response,reverse("knowledge_admin:core_user_changelist"))
        self.assertContains(response,reverse("knowledge_admin:auth_group_changelist"))
        for route,args in [
            ("core_user_changelist",[]),("core_user_add",[]),
            ("core_user_change",[self.target.pk]),("auth_user_password_change",[self.target.pk]),
            ("core_user_delete",[self.target.pk]),("auth_group_changelist",[]),("auth_group_add",[]),
        ]:
            with self.subTest(route=route):
                self.assertEqual(self.client.get(reverse(f"knowledge_admin:{route}",args=args)).status_code,200)

    def test_superuser_can_create_a_user_with_a_hashed_password(self):
        password = "CreatedUserTestPassw0rd!"
        response = self.client.post(reverse("knowledge_admin:core_user_add"),{
            "username":"created-from-admin","usable_password":"true",
            "password1":password,"password2":password,"_save":"Save",
        })
        self.assertEqual(response.status_code,302)
        user = User.objects.get(username="created-from-admin")
        self.assertTrue(user.check_password(password))
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_superuser_can_update_and_deactivate_a_user(self):
        response = self.client.post(reverse("knowledge_admin:core_user_change",args=[self.target.pk]),{
            "username":self.target.username,"email":"updated@example.test",
            "first_name":"Updated","last_name":"User",
            "date_joined_0":self.target.date_joined.strftime("%Y-%m-%d"),
            "date_joined_1":self.target.date_joined.strftime("%H:%M:%S"),"_save":"Save",
        })
        self.assertEqual(response.status_code,302)
        self.target.refresh_from_db()
        self.assertEqual(self.target.email,"updated@example.test")
        self.assertEqual(self.target.first_name,"Updated")
        self.assertFalse(self.target.is_active)
        self.assertTrue(self.target.check_password("OriginalTestPassw0rd!"))

    def test_superuser_can_change_a_users_password(self):
        password = "ChangedUserTestPassw0rd!"
        response = self.client.post(reverse("knowledge_admin:auth_user_password_change",args=[self.target.pk]),{
            "usable_password":"true","password1":password,"password2":password,
        })
        self.assertEqual(response.status_code,302)
        self.target.refresh_from_db()
        self.assertTrue(self.target.check_password(password))

    def test_superuser_can_delete_a_user(self):
        from .taxonomy import ensure_default_categories
        ensure_default_categories(self.target)
        preview = self.client.get(reverse("knowledge_admin:core_user_delete",args=[self.target.pk]))
        self.assertEqual(preview.status_code,200)
        self.assertFalse(preview.context["perms_lacking"])
        self.assertFalse(preview.context["protected"])
        response = self.client.post(reverse("knowledge_admin:core_user_delete",args=[self.target.pk]),{"post":"yes"})
        self.assertEqual(response.status_code,302)
        self.assertFalse(User.objects.filter(pk=self.target.pk).exists())

    def test_staff_without_permissions_cannot_manage_users_or_groups(self):
        self.client.force_login(self.staff)
        for route in ("core_user_changelist","core_user_add","auth_group_changelist"):
            with self.subTest(route=route):
                self.assertEqual(self.client.get(reverse(f"knowledge_admin:{route}")).status_code,403)
        self.assertNotContains(self.client.get(reverse("knowledge_admin:index")),"Users and permissions")

    def test_user_view_permission_does_not_grant_create_or_change_permission(self):
        from django.contrib.auth.models import Permission
        self.staff.user_permissions.add(Permission.objects.get(content_type__app_label="core",codename="view_user"))
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get(reverse("knowledge_admin:core_user_changelist")).status_code,200)
        self.assertEqual(self.client.get(reverse("knowledge_admin:core_user_add")).status_code,403)
        self.assertEqual(self.client.post(reverse("knowledge_admin:core_user_change",args=[self.target.pk]),{"username":"forbidden"}).status_code,403)


    def test_superuser_can_bulk_delete_users_with_uncategorized_categories(self):
        from .taxonomy import ensure_default_categories
        for user in (self.target,self.staff):
            ensure_default_categories(user)
        admin_categories = {Category:list(Category.objects.filter(user=self.admin).values_list("pk",flat=True))
                            for _,Category,_,_ in TAXONOMY_MODELS.values()}
        target_ids = [self.target.pk,self.staff.pk]
        data = {"action":"delete_selected","_selected_action":[str(pk) for pk in target_ids]}
        url = reverse("knowledge_admin:core_user_changelist")
        preview = self.client.post(url,data)
        self.assertEqual(preview.status_code,200)
        self.assertFalse(preview.context["perms_lacking"])
        self.assertFalse(preview.context["protected"])
        response = self.client.post(url,{**data,"post":"yes"})
        self.assertEqual(response.status_code,302)
        self.assertFalse(User.objects.filter(pk__in=target_ids).exists())
        for Category,ids in admin_categories.items():
            self.assertFalse(Category.objects.filter(user_id__in=target_ids).exists())
            self.assertCountEqual(Category.objects.filter(user=self.admin).values_list("pk",flat=True),ids)

    def test_uncategorized_stays_protected_in_admin_for_all_post_types(self):
        for _,Category,_,_ in TAXONOMY_MODELS.values():
            with self.subTest(model=Category._meta.model_name):
                category = Category.objects.get(user=self.admin,slug="uncategorized")
                url = reverse(f"knowledge_admin:core_{Category._meta.model_name}_delete",args=[category.pk])
                for response in (self.client.get(url),self.client.post(url,{"post":"yes"})):
                    self.assertEqual(response.status_code,200)
                    self.assertTrue(response.context["protected"])
                    self.assertFalse(response.context["perms_lacking"])
                self.assertTrue(Category.objects.filter(pk=category.pk).exists())
                bulk = self.client.post(reverse(f"knowledge_admin:core_{Category._meta.model_name}_changelist"),{
                    "action":"delete_selected","_selected_action":[str(category.pk)],"post":"yes",
                })
                self.assertEqual(bulk.status_code,200)
                self.assertTrue(bulk.context["protected"])
                self.assertTrue(Category.objects.filter(pk=category.pk).exists())
