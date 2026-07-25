from django.shortcuts import get_object_or_404, render,redirect
from django.conf import settings
from django.contrib import messages
from django.core.exceptions import ImproperlyConfigured
from django.core.paginator import Paginator
from .models import *
from django.urls import reverse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse, HttpResponseRedirect, JsonResponse
from functools import wraps
from django.db.models import Q
from django.db import transaction
from django.views.decorators.http import require_POST
import secrets
from .forms import (
    ArticleForm, CentralPointForm, DecisionForm, GoalForm,
    JournalForm, NoteForm, RegistrationForm, StrategyForm,
)
from .google_oauth import GoogleOAuthError, authorization_url, fetch_profile
from .taxonomy import (
    DEFAULT_CATEGORY_SLUG, TAXONOMY_MODELS, default_category_first,
    get_default_category, is_category_model,
)
# Create your views here.


RECORD_FORMS = {
    "article": (Article, ArticleForm, "article_single", "index", "Article"),
    "journal": (Journal, JournalForm, "journal_single", "journal_index", "Journal entry"),
    "note": (Note, NoteForm, "note_single", "note_index", "Note"),
    "centralpoint": (CentralPoint, CentralPointForm, "centralpoint_single", "centralpoint_index", "Central point"),
    "strategy": (Strategy, StrategyForm, "strategy_single", "strategy_index", "Strategy"),
    "decision": (Decision, DecisionForm, "decision_single", "decision_index", "Decision"),
    "goal": (Goal, GoalForm, "goal_single", "goal_index", "Goal"),
}

SEARCH_RECORD_TYPES = (
    (Article, "article_single", "fa-regular fa-newspaper", "content"),
    (Journal, "journal_single", "fa-solid fa-book", "content"),
    (Note, "note_single", "fa-solid fa-pen-to-square", "content"),
    (CentralPoint, "centralpoint_single", "fa-solid fa-chess-knight", "content"),
    (Strategy, "strategy_single", "fa-solid fa-chess-king", "finalized_strategy"),
    (Decision, "decision_single", "fa-solid fa-gavel", "recommended_solution"),
    (Goal, "goal_single", "fa-solid fa-medal", "outcome"),
)


def records_for_user(model, user):
    return model.objects.filter(user=user)


def taxonomy_for_user(model, user):
    queryset = model.objects.filter(user=user)
    if is_category_model(model):
        return default_category_first(queryset)
    return queryset.order_by("name")


def workspace_login_required(view):
    @wraps(view)
    def workspace_view(request, *args, username=None, **kwargs):
        if username != request.user.username:
            raise Http404
        return view(request, *args, **kwargs)

    return login_required(workspace_view)


@workspace_login_required
@require_POST
def taxonomy_create(request, record_type):
    models_for_type = TAXONOMY_MODELS.get(record_type)
    if models_for_type is None:
        raise Http404

    kind = request.POST.get("kind", "").strip()
    name = request.POST.get("name", "").strip()
    if kind not in {"category", "subcategory", "tag"}:
        return JsonResponse({"error": "Invalid taxonomy type."}, status=400)
    if not name:
        return JsonResponse({"error": "A name is required."}, status=400)
    if len(name) > 255:
        return JsonResponse(
            {"error": "The name must contain 255 characters or fewer."},
            status=400,
        )

    _, category_model, subcategory_model, tag_model = models_for_type
    model = {"category": category_model, "tag": tag_model}.get(kind)
    create_values = {"user": request.user}

    if kind == "subcategory":
        category_slug = request.POST.get("category_slug", "").strip()
        category = get_object_or_404(
            category_model,
            user=request.user,
            slug=category_slug,
        )
        if category.slug == DEFAULT_CATEGORY_SLUG:
            return JsonResponse(
                {"error": "Uncategorized cannot have subcategories."},
                status=400,
            )
        model = subcategory_model
        create_values["category"] = category

    existing = model.objects.filter(
        user=request.user,
        name__iexact=name,
        **({"category": create_values["category"]} if kind == "subcategory" else {}),
    ).first()
    item = existing or model.objects.create(name=name, **create_values)

    return JsonResponse({
        "created": existing is None,
        "id": item.pk,
        "name": item.name,
        "slug": item.slug,
    })


@workspace_login_required
@require_POST
@transaction.atomic
def taxonomy_delete(request, record_type):
    models_for_type = TAXONOMY_MODELS.get(record_type)
    if models_for_type is None:
        raise Http404

    kind = request.POST.get("kind", "").strip()
    slug = request.POST.get("slug", "").strip()
    if kind not in {"category", "subcategory", "tag"} or not slug:
        return JsonResponse({"error": "Invalid taxonomy item."}, status=400)

    record_model, category_model, subcategory_model, tag_model = models_for_type
    model = {
        "category": category_model,
        "subcategory": subcategory_model,
        "tag": tag_model,
    }[kind]
    item = get_object_or_404(model, user=request.user, slug=slug)

    if kind == "category":
        if item.slug == DEFAULT_CATEGORY_SLUG:
            return JsonResponse(
                {"error": "Uncategorized cannot be deleted."},
                status=400,
            )
        default_category = get_default_category(category_model, request.user)
        record_model.objects.filter(
            user=request.user,
            category=item,
        ).update(category=default_category, subcategory=None)
    elif kind == "subcategory":
        record_model.objects.filter(
            user=request.user,
            subcategory=item,
        ).update(subcategory=None)

    item.delete()
    return JsonResponse({"deleted": True})


@workspace_login_required
def record_search(request):
    query = request.GET.get("q", "").strip()
    results = []

    if query:
        for model, detail_url, icon_class, preview_field in SEARCH_RECORD_TYPES:
            for record in records_for_user(model, request.user).filter(title__icontains=query):
                results.append({
                    "record": record,
                    "detail_url": detail_url,
                    "icon_class": icon_class,
                    "preview": getattr(record, preview_field, ""),
                })

        results.sort(key=lambda result: result["record"].created_at, reverse=True)

    page_obj = Paginator(results, 6).get_page(request.GET.get("page"))
    return render(request, "core/view/search-results.html", {
        "page_obj": page_obj,
        "query": query,
    })


@workspace_login_required
def record_create(request, record_type):
    _, form_class, detail_url, _, label = RECORD_FORMS[record_type]
    form = form_class(request.POST or None, user=request.user)
    if request.method == "POST" and form.is_valid():
        form.instance.user = request.user
        record = form.save()
        return redirect(detail_url, username=request.user.username, slug=record.slug)
    return render(request, "core/forms/record-form.html", {
        "form": form,
        "record_type": record_type,
        "record_label": label,
        "is_edit": False,
    })


@workspace_login_required
def record_update(request, record_type, slug):
    model, form_class, detail_url, index_url, label = RECORD_FORMS[record_type]
    record = get_object_or_404(model, slug=slug, user=request.user)

    if request.method == "POST" and request.POST.get("action") == "delete":
        record.delete()
        return redirect(index_url, username=request.user.username)

    form = form_class(request.POST or None, instance=record, user=request.user)
    if request.method == "POST" and form.is_valid():
        record = form.save()
        return redirect(detail_url, username=request.user.username, slug=record.slug)

    return render(request, "core/forms/record-form.html", {
        "form": form,
        "record": record,
        "record_type": record_type,
        "record_label": label,
        "is_edit": True,
    })



def login_view(request):
    if request.method == "POST":

        # Attempt to sign user in
        identifier = request.POST["username"].strip()
        password = request.POST["password"]
        matches = list(User.objects.filter(
            Q(username=identifier) | Q(email__iexact=identifier)
        ).values_list("username", flat=True)[:2])
        authentication_username = matches[0] if len(matches) == 1 else identifier
        user = authenticate(
            request,
            username=authentication_username,
            password=password,
        )

        # Check if authentication successful
        if user is not None:
            login(request, user)
            return redirect("index", username=user.username)
        else:
            return render(request, "core/login.html", {
                "message": "Invalid username/email or password."
            })
    else:
        return render(request, "core/login.html")


def root_redirect(request):
    if request.user.is_authenticated:
        return redirect("index", username=request.user.username)
    return redirect("login")


def register_view(request):
    if request.user.is_authenticated:
        return redirect("index", username=request.user.username)

    form = RegistrationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        messages.success(request, "Welcome! Your account has been created.")
        return redirect("login")
    google_client_id = getattr(settings, "GOOGLE_OAUTH_CLIENT_ID", "")
    google_client_secret = getattr(settings, "GOOGLE_OAUTH_CLIENT_SECRET", "")
    return render(request, "core/register.html", {
        "form": form,
        "google_enabled": bool(google_client_id and google_client_secret),
    })


def google_login(request):
    callback_url = request.build_absolute_uri(reverse("google_callback"))
    try:
        return redirect(authorization_url(request, callback_url))
    except ImproperlyConfigured:
        messages.error(request, "Google registration has not been configured yet.")
        return redirect("register")


def google_callback(request):
    returned_state = request.GET.get("state", "")
    expected_state = request.session.pop("google_oauth_state", "")
    if not expected_state or not secrets.compare_digest(returned_state, expected_state):
        messages.error(request, "The Google sign-in request expired. Please try again.")
        return redirect("register")
    if request.GET.get("error"):
        messages.error(request, "Google sign-in was cancelled.")
        return redirect("register")

    code = request.GET.get("code")
    if not code:
        messages.error(request, "Google did not provide an authorization code.")
        return redirect("register")

    callback_url = request.build_absolute_uri(reverse("google_callback"))
    try:
        profile = fetch_profile(code, callback_url)
    except (GoogleOAuthError, ImproperlyConfigured):
        messages.error(request, "Google sign-in could not be completed. Please try again.")
        return redirect("register")

    email = profile["email"].strip().lower()
    user = User.objects.filter(email__iexact=email).first()
    if user is None:
        base_username = (email.split("@", 1)[0] or "google-user")[:140]
        username = base_username
        suffix = 1
        while User.objects.filter(username=username).exists():
            suffix += 1
            username = f"{base_username[:145 - len(str(suffix))]}-{suffix}"
        user = User(
            username=username,
            email=email,
            first_name=profile.get("given_name", "")[:150],
            last_name=profile.get("family_name", "")[:150],
        )
        user.set_unusable_password()
        user.save()

    login(request, user, backend="core.backends.UsernameOrEmailBackend")
    messages.success(request, "You are signed in with Google.")
    return redirect("index", username=user.username)


def logout_view(request):
    logout(request)
    return redirect("login")


# ARTICLES
@workspace_login_required
def index(request):
    articles = records_for_user(Article, request.user).order_by("-created_at")
    paginator = Paginator(articles, 6) # Show 9 per page.
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    article_tags = taxonomy_for_user(ArticleTag, request.user)

    article_categories = taxonomy_for_user(ArticleCategory, request.user)
    for category in article_categories:
        category.sub_categories = category.subcategories.filter(user=request.user)

    return render(request,"core/view/index.html",{
        "articles":articles,
        "page_obj":page_obj,
        "article_categories":article_categories,  
        "article_tags":article_tags     
    })

@workspace_login_required
def article_single(request,slug):
    article = get_object_or_404(Article, slug=slug, user=request.user)
    article_categories = taxonomy_for_user(ArticleCategory, request.user)
    article_tags = taxonomy_for_user(ArticleTag, request.user)
    for category in article_categories:
        category.sub_categories = category.subcategories.filter(user=request.user)

    return render(request,"core/singles/article-single.html",{
        "article":article,
        "article_categories":article_categories,
        "article_tags":article_tags,
        
        
    })

@workspace_login_required
def article_category(request,slug):
    article_categories = taxonomy_for_user(ArticleCategory, request.user)
    article_category = get_object_or_404(ArticleCategory, slug=slug, user=request.user)
    article_tags = taxonomy_for_user(ArticleTag, request.user)
    articles = records_for_user(Article, request.user).filter(category=article_category).order_by("-created_at")
    paginator = Paginator(articles, 6) # Show 9 per page.
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

   
    for category in article_categories:
        category.sub_categories = category.subcategories.filter(user=request.user)
    return render(request,"core/categories/article-category.html",{
        "page_obj":page_obj,
        "article_category":article_category,
        "article_categories":article_categories,
        "article_tags":article_tags,
        
    })

@workspace_login_required
def article_subcategory(request,cat_slug,subcat_slug):
    article_categories = taxonomy_for_user(ArticleCategory, request.user)
    article_subcategory = get_object_or_404(
        ArticleSubcategory, slug=subcat_slug, user=request.user,
        category__slug=cat_slug,
    )
    article_tags = taxonomy_for_user(ArticleTag, request.user)
    articles = records_for_user(Article, request.user).filter(subcategory=article_subcategory).order_by("-created_at")
    paginator = Paginator(articles, 6) # Show 9 per page.
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

   
    for category in article_categories:
        category.sub_categories = category.subcategories.filter(user=request.user)
    return render(request,"core/subcategories/article-subcategory.html",{
        "page_obj":page_obj,
        "article_category":article_category,
        "article_categories":article_categories,
        "article_subcategory":article_subcategory,
        "article_tags":article_tags,
        
    })

@workspace_login_required
def article_tag(request,slug):
    article_categories = taxonomy_for_user(ArticleCategory, request.user)
    article_tags = taxonomy_for_user(ArticleTag, request.user)
    article_tag = get_object_or_404(ArticleTag, slug=slug, user=request.user)
    articles = records_for_user(Article, request.user).filter(tags=article_tag).order_by("-created_at")
    paginator = Paginator(articles, 6) # Show 9 per page.
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

   
    for category in article_categories:
        category.sub_categories = category.subcategories.filter(user=request.user)
    return render(request,"core/tags/article-tags.html",{
        "page_obj":page_obj,
        "article_category":article_category,
        "article_categories":article_categories,
        "article_tag":article_tag,
        "article_tags":article_tags,
        
    })

# JOURNALS
@workspace_login_required
def journal_index(request):

    journals = records_for_user(Journal, request.user).order_by("-created_at")
    paginator = Paginator(journals, 6) # Show 9 per page.
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    journal_tags = taxonomy_for_user(JournalTag, request.user)

    journal_categories = taxonomy_for_user(JournalCategory, request.user)
    for category in journal_categories:
        category.sub_categories = category.subcategories.filter(user=request.user)

    return render(request,"core/view/journal.html",{
        "article":journals,
        "page_obj":page_obj,
        "article_categories":journal_categories,  
        "article_tags":journal_tags     
    })

@workspace_login_required
def journal_single(request,slug):
    article = get_object_or_404(Journal, slug=slug, user=request.user)
    journal_categories = taxonomy_for_user(JournalCategory, request.user)
    journal_tags = taxonomy_for_user(JournalTag, request.user)
    for category in journal_categories:
        category.sub_categories = category.subcategories.filter(user=request.user)

    return render(request,"core/singles/journal-single.html",{
        "article":article,
        "article_categories":journal_categories,
        "article_tags":journal_tags,
        
        
    })

@workspace_login_required
def journal_category(request,slug):
    journal_categories = taxonomy_for_user(JournalCategory, request.user)
    journal_category = get_object_or_404(JournalCategory, slug=slug, user=request.user)
    journal_tags = taxonomy_for_user(JournalTag, request.user)
    articles = records_for_user(Journal, request.user).filter(category=journal_category).order_by("-created_at")
    paginator = Paginator(articles, 6) # Show 9 per page.
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

   
    for category in journal_categories:
        category.sub_categories = category.subcategories.filter(user=request.user)
    return render(request,"core/categories/journal-category.html",{
        "page_obj":page_obj,
        "article_category":journal_category,
        "article_categories":journal_categories,
        "article_tags":journal_tags,
        
    })

@workspace_login_required
def journal_subcategory(request,cat_slug,subcat_slug):
    journal_categories = taxonomy_for_user(JournalCategory, request.user)
    journal_subcategory = get_object_or_404(
        JournalSubcategory, slug=subcat_slug, user=request.user,
        category__slug=cat_slug,
    )
    journal_tags = taxonomy_for_user(JournalTag, request.user)
    articles = records_for_user(Journal, request.user).filter(subcategory=journal_subcategory).order_by("-created_at")
    paginator = Paginator(articles, 6) # Show 9 per page.
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

   
    for category in journal_categories:
        category.sub_categories = category.subcategories.filter(user=request.user)
    return render(request,"core/subcategories/journal-subcategory.html",{
        "page_obj":page_obj,
        "article_categories":journal_categories,
        "article_subcategory":journal_subcategory,
        "article_tags":journal_tags,
        
    })
@workspace_login_required
def journal_tag(request,slug):
    article_categories = taxonomy_for_user(JournalCategory, request.user)
    article_tags = taxonomy_for_user(JournalTag, request.user)
    article_tag = get_object_or_404(JournalTag, slug=slug, user=request.user)
    articles = records_for_user(Journal, request.user).filter(tags=article_tag).order_by("-created_at")
    paginator = Paginator(articles, 6) # Show 9 per page.
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

   
    for category in article_categories:
        category.sub_categories = category.subcategories.filter(user=request.user)
    return render(request,"core/tags/journal-tags.html",{
        "page_obj":page_obj,
        "article_category":article_category,
        "article_categories":article_categories,
        "article_tag":article_tag,
        "article_tags":article_tags,
        
    })

# NOTES
@workspace_login_required
def note_index(request):

    notes = records_for_user(Note, request.user).order_by("-created_at")
    paginator = Paginator(notes, 6) # Show 9 per page.
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    note_tags = taxonomy_for_user(NoteTag, request.user)
    note_categories = taxonomy_for_user(NoteCategory, request.user)
    for category in note_categories:
        category.sub_categories = category.subcategories.filter(user=request.user)

    return render(request,"core/view/note.html",{
        "article":notes,
        "page_obj":page_obj,
        "article_categories":note_categories,  
        "article_tags":note_tags     
    })

@workspace_login_required
def note_single(request,slug):
    article = get_object_or_404(Note, slug=slug, user=request.user)
    note_categories = taxonomy_for_user(NoteCategory, request.user)
    note_tags = taxonomy_for_user(NoteTag, request.user)
    for category in note_categories:
        category.sub_categories = category.subcategories.filter(user=request.user)

    return render(request,"core/singles/note-single.html",{
        "article":article,
        "article_categories":note_categories,
        "article_tags":note_tags,
        
        
    })

@workspace_login_required
def note_category(request,slug):
    note_categories = taxonomy_for_user(NoteCategory, request.user)
    note_category = get_object_or_404(NoteCategory, slug=slug, user=request.user)
    note_tags = taxonomy_for_user(NoteTag, request.user)
    articles = records_for_user(Note, request.user).filter(category=note_category).order_by("-created_at")
    paginator = Paginator(articles, 6) # Show 9 per page.
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

   
    for category in note_categories:
        category.sub_categories = category.subcategories.filter(user=request.user)
    return render(request,"core/categories/note-category.html",{
        "page_obj":page_obj,
        "article_category":note_category,
        "article_categories":note_categories,
        "article_tags":note_tags,
        
    })

@workspace_login_required
def note_subcategory(request,cat_slug,subcat_slug):
    note_categories = taxonomy_for_user(NoteCategory, request.user)
    note_subcategory = get_object_or_404(
        NoteSubcategory, slug=subcat_slug, user=request.user,
        category__slug=cat_slug,
    )
    note_tags = taxonomy_for_user(NoteTag, request.user)
    articles = records_for_user(Note, request.user).filter(subcategory=note_subcategory).order_by("-created_at")
    paginator = Paginator(articles, 6) # Show 9 per page.
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

   
    for category in note_categories:
        category.sub_categories = category.subcategories.filter(user=request.user)
    return render(request,"core/subcategories/note-subcategory.html",{
        "page_obj":page_obj,
        "article_categories":note_categories,
        "article_subcategory":note_subcategory,
        "article_tags":note_tags,
        
    })

@workspace_login_required
def note_tag(request,slug):
    article_categories = taxonomy_for_user(NoteCategory, request.user)
    article_tags = taxonomy_for_user(NoteTag, request.user)
    article_tag = get_object_or_404(NoteTag, slug=slug, user=request.user)
    articles = records_for_user(Note, request.user).filter(tags=article_tag).order_by("-created_at")
    paginator = Paginator(articles, 6) # Show 9 per page.
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

   
    for category in article_categories:
        category.sub_categories = category.subcategories.filter(user=request.user)
    return render(request,"core/tags/note-tags.html",{
        "page_obj":page_obj,
        "article_category":article_category,
        "article_categories":article_categories,
        "article_tag":article_tag,
        "article_tags":article_tags,
        
    })

# CENTRAL POINT

@workspace_login_required
def centralpoint_index(request):

    articles = records_for_user(CentralPoint, request.user).order_by("-created_at")
    paginator = Paginator(articles, 6) # Show 9 per page.
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    article_tags = taxonomy_for_user(CentralPointTag, request.user)

    article_categories = taxonomy_for_user(CentralPointCategory, request.user)
    for category in article_categories:
        category.sub_categories = category.subcategories.filter(user=request.user)

    return render(request,"core/view/centralpoint.html",{
        "articles":articles,
        "page_obj":page_obj,
        "article_categories":article_categories,  
        "article_tags":article_tags     
    })

@workspace_login_required
def centralpoint_single(request,slug):
    article = get_object_or_404(CentralPoint, slug=slug, user=request.user)
    article_categories = taxonomy_for_user(CentralPointCategory, request.user)
    article_tags = taxonomy_for_user(CentralPointTag, request.user)
    for category in article_categories:
        category.sub_categories = category.subcategories.filter(user=request.user)

    return render(request,"core/singles/centralpoint-single.html",{
        "article":article,
        "article_categories":article_categories,
        "article_tags":article_tags,
        
        
    })

@workspace_login_required
def centralpoint_category(request,slug):
    article_categories = taxonomy_for_user(CentralPointCategory, request.user)
    article_category = get_object_or_404(CentralPointCategory, slug=slug, user=request.user)
    article_tags = taxonomy_for_user(CentralPointTag, request.user)
    articles = records_for_user(CentralPoint, request.user).filter(category=article_category).order_by("-created_at")
    paginator = Paginator(articles, 6) # Show 9 per page.
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

   
    for category in article_categories:
        category.sub_categories = category.subcategories.filter(user=request.user)
    return render(request,"core/categories/centralpoint-category.html",{
        "page_obj":page_obj,
        "article_category":article_category,
        "article_categories":article_categories,
        "article_tags":article_tags,
        
    })

@workspace_login_required
def centralpoint_subcategory(request,cat_slug,subcat_slug):
    article_categories = taxonomy_for_user(CentralPointCategory, request.user)
    article_subcategory = get_object_or_404(
        CentralPointSubcategory, slug=subcat_slug, user=request.user,
        category__slug=cat_slug,
    )
    article_tags = taxonomy_for_user(CentralPointTag, request.user)
    articles = records_for_user(CentralPoint, request.user).filter(subcategory=article_subcategory).order_by("-created_at")
    paginator = Paginator(articles, 6) # Show 9 per page.
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

   
    for category in article_categories:
        category.sub_categories = category.subcategories.filter(user=request.user)
    return render(request,"core/subcategories/centralpoint-subcategory.html",{
        "page_obj":page_obj,
        "article_category":article_category,
        "article_categories":article_categories,
        "article_subcategory":article_subcategory,
        "article_tags":article_tags,
        
    })

@workspace_login_required
def centralpoint_tag(request,slug):
    article_categories = taxonomy_for_user(CentralPointCategory, request.user)
    article_tags = taxonomy_for_user(CentralPointTag, request.user)
    article_tag = get_object_or_404(CentralPointTag, slug=slug, user=request.user)
    articles = records_for_user(CentralPoint, request.user).filter(tags=article_tag).order_by("-created_at")
    paginator = Paginator(articles, 6) # Show 9 per page.
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

   
    for category in article_categories:
        category.sub_categories = category.subcategories.filter(user=request.user)
    return render(request,"core/tags/centralpoint-tags.html",{
        "page_obj":page_obj,
        "article_category":article_category,
        "article_categories":article_categories,
        "article_tag":article_tag,
        "article_tags":article_tags,
        
    })

# STRATEGY
@workspace_login_required
def strategy_index(request):


    articles = records_for_user(Strategy, request.user).order_by("-created_at")
    paginator = Paginator(articles, 6) # Show 9 per page.
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    article_tags = taxonomy_for_user(StrategyTag, request.user)

    article_categories = taxonomy_for_user(StrategyCategory, request.user)
    for category in article_categories:
        category.sub_categories = category.subcategories.filter(user=request.user)
    
  
  

    return render(request,"core/view/strategy.html",{
        "articles":articles,
        "page_obj":page_obj,
        "article_categories":article_categories,  
        "article_tags":article_tags,
    })
@workspace_login_required
def strategy_single(request,slug):
    article = get_object_or_404(Strategy, slug=slug, user=request.user)
    article_categories = taxonomy_for_user(StrategyCategory, request.user)
    article_tags = taxonomy_for_user(StrategyTag, request.user)
    for category in article_categories:
        category.sub_categories = category.subcategories.filter(user=request.user)

    return render(request,"core/singles/strategy-single.html",{
        "article":article,
        "article_categories":article_categories,
        "article_tags":article_tags,
        
        
    })
@workspace_login_required
def strategy_category(request,slug):

    article_categories = taxonomy_for_user(StrategyCategory, request.user)
    article_category = get_object_or_404(StrategyCategory, slug=slug, user=request.user)
    articles = records_for_user(Strategy, request.user).filter(category=article_category).order_by("-created_at")
    paginator = Paginator(articles, 6) # Show 9 per page.
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    article_tags = taxonomy_for_user(StrategyTag, request.user)


    article_categories = taxonomy_for_user(StrategyCategory, request.user)
    for category in article_categories:
        category.sub_categories = category.subcategories.filter(user=request.user)

    return render(request,"core/categories/strategy-category.html",{
        "page_obj":page_obj,
        "article_category":article_category,
        "article_categories":article_categories,
        "article_tags":article_tags,
        
    })
@workspace_login_required
def strategy_subcategory(request,cat_slug,subcat_slug):
    article_categories = taxonomy_for_user(StrategyCategory, request.user)
    article_subcategory = get_object_or_404(
        StrategySubcategory, slug=subcat_slug, user=request.user,
        category__slug=cat_slug,
    )
    article_tags = taxonomy_for_user(StrategyTag, request.user)
    articles = records_for_user(Strategy, request.user).filter(subcategory=article_subcategory).order_by("-created_at")
    paginator = Paginator(articles, 6) # Show 9 per page.
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

   
    for category in article_categories:
        category.sub_categories = category.subcategories.filter(user=request.user)
    return render(request,"core/subcategories/strategy-subcategory.html",{
        "page_obj":page_obj,
        "article_category":article_category,
        "article_categories":article_categories,
        "article_subcategory":article_subcategory,
        "article_tags":article_tags,
        
    })
@workspace_login_required
def strategy_tag(request,slug):
    article_categories = taxonomy_for_user(StrategyCategory, request.user)
    article_tags = taxonomy_for_user(StrategyTag, request.user)
    article_tag = get_object_or_404(StrategyTag, slug=slug, user=request.user)
    articles = records_for_user(Strategy, request.user).filter(tags=article_tag).order_by("-created_at")
    paginator = Paginator(articles, 6) # Show 9 per page.
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

   
    for category in article_categories:
        category.sub_categories = category.subcategories.filter(user=request.user)
    return render(request,"core/tags/strategy-tags.html",{
        "page_obj":page_obj,
        "article_category":article_category,
        "article_categories":article_categories,
        "article_tag":article_tag,
        "article_tags":article_tags,
        
    })

# DECISION
@workspace_login_required
def decision_index(request):


    articles = records_for_user(Decision, request.user).order_by("-created_at")
    paginator = Paginator(articles, 6) # Show 9 per page.
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    article_tags = taxonomy_for_user(DecisionTag, request.user)

    article_categories = taxonomy_for_user(DecisionCategory, request.user)
    for category in article_categories:
        category.sub_categories = category.subcategories.filter(user=request.user)
    
  
  

    return render(request,"core/view/decision.html",{
        "articles":articles,
        "page_obj":page_obj,
        "article_categories":article_categories,  
        "article_tags":article_tags,
    })
@workspace_login_required
def decision_single(request,slug):
    article = get_object_or_404(Decision, slug=slug, user=request.user)
    article_categories = taxonomy_for_user(DecisionCategory, request.user)
    article_tags = taxonomy_for_user(DecisionTag, request.user)
    for category in article_categories:
        category.sub_categories = category.subcategories.filter(user=request.user)

    return render(request,"core/singles/decision-single.html",{
        "article":article,
        "article_categories":article_categories,
        "article_tags":article_tags,
        
        
    })
@workspace_login_required
def decision_category(request,slug):

    article_categories = taxonomy_for_user(DecisionCategory, request.user)
    article_category = get_object_or_404(DecisionCategory, slug=slug, user=request.user)
    articles = records_for_user(Decision, request.user).filter(category=article_category).order_by("-created_at")
    paginator = Paginator(articles, 6) # Show 9 per page.
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    article_tags = taxonomy_for_user(DecisionTag, request.user)


    article_categories = taxonomy_for_user(DecisionCategory, request.user)
    for category in article_categories:
        category.sub_categories = category.subcategories.filter(user=request.user)

    return render(request,"core/categories/decision-category.html",{
        "page_obj":page_obj,
        "article_category":article_category,
        "article_categories":article_categories,
        "article_tags":article_tags,
        
    })
@workspace_login_required
def decision_subcategory(request,cat_slug,subcat_slug):
    article_categories = taxonomy_for_user(DecisionCategory, request.user)
    article_subcategory = get_object_or_404(
        DecisionSubcategory, slug=subcat_slug, user=request.user,
        category__slug=cat_slug,
    )
    article_tags = taxonomy_for_user(DecisionTag, request.user)
    articles = records_for_user(Decision, request.user).filter(subcategory=article_subcategory).order_by("-created_at")
    paginator = Paginator(articles, 6) # Show 9 per page.
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

   
    for category in article_categories:
        category.sub_categories = category.subcategories.filter(user=request.user)
    return render(request,"core/subcategories/decision-subcategory.html",{
        "page_obj":page_obj,
        "article_category":article_category,
        "article_categories":article_categories,
        "article_subcategory":article_subcategory,
        "article_tags":article_tags,
        
    })
@workspace_login_required
def decision_tag(request,slug):
    article_categories = taxonomy_for_user(DecisionCategory, request.user)
    article_tags = taxonomy_for_user(DecisionTag, request.user)
    article_tag = get_object_or_404(DecisionTag, slug=slug, user=request.user)
    articles = records_for_user(Decision, request.user).filter(tags=article_tag).order_by("-created_at")
    paginator = Paginator(articles, 6) # Show 9 per page.
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

   
    for category in article_categories:
        category.sub_categories = category.subcategories.filter(user=request.user)
    return render(request,"core/tags/decision-tags.html",{
        "page_obj":page_obj,
        "article_category":article_category,
        "article_categories":article_categories,
        "article_tag":article_tag,
        "article_tags":article_tags,
        
    })

# GOAL
@workspace_login_required
def goal_index(request):


    articles = records_for_user(Goal, request.user).order_by("-created_at")
    paginator = Paginator(articles, 6) # Show 9 per page.
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    article_tags = taxonomy_for_user(GoalTag, request.user)

    article_categories = taxonomy_for_user(GoalCategory, request.user)
    for category in article_categories:
        category.sub_categories = category.subcategories.filter(user=request.user)
    
  
  

    return render(request,"core/view/goal.html",{
        "articles":articles,
        "page_obj":page_obj,
        "article_categories":article_categories,  
        "article_tags":article_tags,
    })
@workspace_login_required
def goal_single(request,slug):
    article = get_object_or_404(Goal, slug=slug, user=request.user)
    article_categories = taxonomy_for_user(GoalCategory, request.user)
    article_tags = taxonomy_for_user(GoalTag, request.user)
    for category in article_categories:
        category.sub_categories = category.subcategories.filter(user=request.user)

    return render(request,"core/singles/goal-single.html",{
        "article":article,
        "article_categories":article_categories,
        "article_tags":article_tags,
        
        
    })
@workspace_login_required
def goal_category(request,slug):

    article_categories = taxonomy_for_user(GoalCategory, request.user)
    article_category = get_object_or_404(GoalCategory, slug=slug, user=request.user)
    articles = records_for_user(Goal, request.user).filter(category=article_category).order_by("-created_at")
    paginator = Paginator(articles, 6) # Show 9 per page.
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    article_tags = taxonomy_for_user(GoalTag, request.user)


    article_categories = taxonomy_for_user(GoalCategory, request.user)
    for category in article_categories:
        category.sub_categories = category.subcategories.filter(user=request.user)

    return render(request,"core/categories/goal-category.html",{
        "page_obj":page_obj,
        "article_category":article_category,
        "article_categories":article_categories,
        "article_tags":article_tags,
        
    })
@workspace_login_required
def goal_subcategory(request,cat_slug,subcat_slug):
    article_categories = taxonomy_for_user(GoalCategory, request.user)
    article_subcategory = get_object_or_404(
        GoalSubcategory, slug=subcat_slug, user=request.user,
        category__slug=cat_slug,
    )
    article_tags = taxonomy_for_user(GoalTag, request.user)
    articles = records_for_user(Goal, request.user).filter(subcategory=article_subcategory).order_by("-created_at")
    paginator = Paginator(articles, 6) # Show 9 per page.
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

   
    for category in article_categories:
        category.sub_categories = category.subcategories.filter(user=request.user)
    return render(request,"core/subcategories/goal-subcategory.html",{
        "page_obj":page_obj,
        "article_category":article_category,
        "article_categories":article_categories,
        "article_subcategory":article_subcategory,
        "article_tags":article_tags,
        
    })
@workspace_login_required
def goal_tag(request,slug):
    article_categories = taxonomy_for_user(GoalCategory, request.user)
    article_tags = taxonomy_for_user(GoalTag, request.user)
    article_tag = get_object_or_404(GoalTag, slug=slug, user=request.user)
    articles = records_for_user(Goal, request.user).filter(tags=article_tag).order_by("-created_at")
    paginator = Paginator(articles, 6) # Show 9 per page.
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

   
    for category in article_categories:
        category.sub_categories = category.subcategories.filter(user=request.user)
    return render(request,"core/tags/goal-tags.html",{
        "page_obj":page_obj,
        "article_category":article_category,
        "article_categories":article_categories,
        "article_tag":article_tag,
        "article_tags":article_tags,
        
    })
