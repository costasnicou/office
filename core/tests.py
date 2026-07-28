import base64
import tempfile
from django.conf import settings
from django.test import TestCase, override_settings
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

    def test_create_form_only_shows_the_logged_in_users_taxonomy(self):
        other_user = User.objects.create_user(username="taxonomy-other")
        ArticleCategory.objects.create(user=self.user, name="My category")
        ArticleCategory.objects.create(user=other_user, name="Other category")
        ArticleTag.objects.create(user=self.user, name="My tag")
        ArticleTag.objects.create(user=other_user, name="Other tag")
        self.client.force_login(self.user)

        response = self.client.get(workspace_reverse("article_create", self.user))

        self.assertContains(response, "My category")
        self.assertContains(response, "My tag")
        self.assertNotContains(response, "Other category")
        self.assertNotContains(response, "Other tag")

    def test_users_can_create_taxonomy_with_the_same_name(self):
        other_user = User.objects.create_user(username="same-name-other")
        ArticleCategory.objects.create(user=other_user, name="Work")
        ArticleTag.objects.create(user=other_user, name="Important")
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
        self.assertContains(response, "taxonomy-menu.js?v=20260726-2")
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
        tag = ArticleTag.objects.create(user=self.user, name="Temporary tag")
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
        })

        self.assertEqual(response.status_code, 200)
        self.assertFalse(ArticleTag.objects.filter(pk=tag.pk).exists())
        self.assertFalse(article.tags.exists())

    def test_deletion_redirect_url_is_unfiltered_index_for_each_record_type(self):
        index_routes = {
            record_type: models_for_type[0]._meta.model_name + "_index"
            for record_type, models_for_type in TAXONOMY_MODELS.items()
        }
        index_routes["article"] = "index"

        for record_type, models_for_type in TAXONOMY_MODELS.items():
            tag_model = models_for_type[3]
            tag = tag_model.objects.create(
                user=self.user,
                name=f"{record_type} redirect tag",
            )

            with self.subTest(record_type=record_type):
                response = self.client.post(
                    self.taxonomy_delete_url(record_type),
                    {"kind": "tag", "slug": tag.slug},
                )

                self.assertEqual(response.status_code, 200)
                self.assertEqual(
                    response.json()["redirect_url"],
                    workspace_reverse(index_routes[record_type], self.user),
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
