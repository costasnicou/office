from django.shortcuts import render,redirect
from django.core.paginator import Paginator
from .models import *
from django.urls import reverse
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseRedirect
# Create your views here.



def login_view(request):
    if request.method == "POST":

        # Attempt to sign user in
        username = request.POST["username"]
        password = request.POST["password"]
        user = authenticate(request, username=username, password=password)

        # Check if authentication successful
        if user is not None:
            login(request, user)
            return HttpResponseRedirect(reverse("index"))
        else:
            return render(request, "core/login.html", {
                "message": "Invalid username and/or password."
            })
    else:
        return render(request, "core/login.html")


def logout_view(request):
    logout(request)
    return HttpResponseRedirect(reverse("index"))


# ARTICLES
@login_required
def index(request):
    articles = Article.objects.all().order_by("-created_at")
    paginator = Paginator(articles, 6) # Show 9 per page.
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    article_tags = ArticleTag.objects.all()

    article_categories = ArticleCategory.objects.all()
    for category in article_categories:
        category.sub_categories = category.subcategories.all()

    return render(request,"core/view/index.html",{
        "articles":articles,
        "page_obj":page_obj,
        "article_categories":article_categories,  
        "article_tags":article_tags     
    })

@login_required
def article_single(request,slug):
    article = Article.objects.get(slug=slug)
    article_categories = ArticleCategory.objects.all()
    article_tags = ArticleTag.objects.all()
    for category in article_categories:
        category.sub_categories = category.subcategories.all()

    return render(request,"core/singles/article-single.html",{
        "article":article,
        "article_categories":article_categories,
        "article_tags":article_tags,
        
        
    })

@login_required
def article_category(request,slug):
    article_categories = ArticleCategory.objects.all()
    article_category = ArticleCategory.objects.get(slug=slug)
    article_tags = ArticleTag.objects.all()
    articles = Article.objects.filter(category=article_category).order_by("-created_at")
    paginator = Paginator(articles, 6) # Show 9 per page.
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

   
    for category in article_categories:
        category.sub_categories = category.subcategories.all()
    return render(request,"core/categories/article-category.html",{
        "page_obj":page_obj,
        "article_category":article_category,
        "article_categories":article_categories,
        "article_tags":article_tags,
        
    })

@login_required
def article_subcategory(request,cat_slug,subcat_slug):
    article_categories = ArticleCategory.objects.all()
    article_subcategory = ArticleSubcategory.objects.get(slug=subcat_slug)
    article_tags = ArticleTag.objects.all()
    articles = Article.objects.filter(subcategory=article_subcategory).order_by("-created_at")
    paginator = Paginator(articles, 6) # Show 9 per page.
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

   
    for category in article_categories:
        category.sub_categories = category.subcategories.all()
    return render(request,"core/subcategories/article-subcategory.html",{
        "page_obj":page_obj,
        "article_category":article_category,
        "article_categories":article_categories,
        "article_subcategory":article_subcategory,
        "article_tags":article_tags,
        
    })

@login_required
def article_tag(request,slug):
    article_categories = ArticleCategory.objects.all()
    article_tags = ArticleTag.objects.all()
    article_tag = ArticleTag.objects.get(slug=slug)
    articles = Article.objects.filter(tags=article_tag).order_by("-created_at")
    paginator = Paginator(articles, 6) # Show 9 per page.
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

   
    for category in article_categories:
        category.sub_categories = category.subcategories.all()
    return render(request,"core/tags/article-tags.html",{
        "page_obj":page_obj,
        "article_category":article_category,
        "article_categories":article_categories,
        "article_tag":article_tag,
        "article_tags":article_tags,
        
    })

# JOURNALS
@login_required
def journal_index(request):

    journals = Journal.objects.all().order_by("-created_at")
    paginator = Paginator(journals, 6) # Show 9 per page.
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    journal_tags = JournalTag.objects.all()

    journal_categories = JournalCategory.objects.all()
    for category in journal_categories:
        category.sub_categories = category.subcategories.all()

    return render(request,"core/view/journal.html",{
        "article":journals,
        "page_obj":page_obj,
        "article_categories":journal_categories,  
        "article_tags":journal_tags     
    })

@login_required
def journal_single(request,slug):
    article = Journal.objects.get(slug=slug)
    journal_categories = JournalCategory.objects.all()
    journal_tags = JournalTag.objects.all()
    for category in journal_categories:
        category.sub_categories = category.subcategories.all()

    return render(request,"core/singles/journal-single.html",{
        "article":article,
        "article_categories":journal_categories,
        "article_tags":journal_tags,
        
        
    })

@login_required
def journal_category(request,slug):
    journal_categories = JournalCategory.objects.all()
    journal_category = JournalCategory.objects.get(slug=slug)
    journal_tags = JournalTag.objects.all()
    articles = Journal.objects.filter(category=journal_category).order_by("-created_at")
    paginator = Paginator(articles, 6) # Show 9 per page.
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

   
    for category in journal_categories:
        category.sub_categories = category.subcategories.all()
    return render(request,"core/categories/journal-category.html",{
        "page_obj":page_obj,
        "article_category":journal_category,
        "article_categories":journal_categories,
        "article_tags":journal_tags,
        
    })

@login_required
def journal_subcategory(request,cat_slug,subcat_slug):
    journal_categories = JournalCategory.objects.all()
    journal_subcategory = JournalSubcategory.objects.get(slug=subcat_slug)
    journal_tags = JournalTag.objects.all()
    articles = Journal.objects.filter(subcategory=journal_subcategory).order_by("-created_at")
    paginator = Paginator(articles, 6) # Show 9 per page.
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

   
    for category in journal_categories:
        category.sub_categories = category.subcategories.all()
    return render(request,"core/subcategories/journal-subcategory.html",{
        "page_obj":page_obj,
        "article_categories":journal_categories,
        "article_subcategory":journal_subcategory,
        "article_tags":journal_tags,
        
    })
@login_required
def journal_tag(request,slug):
    article_categories = JournalCategory.objects.all()
    article_tags = JournalTag.objects.all()
    article_tag = JournalTag.objects.get(slug=slug)
    articles = Journal.objects.filter(tags=article_tag).order_by("-created_at")
    paginator = Paginator(articles, 6) # Show 9 per page.
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

   
    for category in article_categories:
        category.sub_categories = category.subcategories.all()
    return render(request,"core/tags/journal-tags.html",{
        "page_obj":page_obj,
        "article_category":article_category,
        "article_categories":article_categories,
        "article_tag":article_tag,
        "article_tags":article_tags,
        
    })

# NOTES
@login_required
def note_index(request):

    notes = Note.objects.all().order_by("-created_at")
    paginator = Paginator(notes, 6) # Show 9 per page.
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    note_tags = NoteTag.objects.all()
    note_categories = NoteCategory.objects.all()
    for category in note_categories:
        category.sub_categories = category.subcategories.all()

    return render(request,"core/view/note.html",{
        "article":notes,
        "page_obj":page_obj,
        "article_categories":note_categories,  
        "article_tags":note_tags     
    })

@login_required
def note_single(request,slug):
    article = Note.objects.get(slug=slug)
    note_categories = NoteCategory.objects.all()
    note_tags = NoteTag.objects.all()
    for category in note_categories:
        category.sub_categories = category.subcategories.all()

    return render(request,"core/singles/note-single.html",{
        "article":article,
        "article_categories":note_categories,
        "article_tags":note_tags,
        
        
    })

@login_required
def note_category(request,slug):
    note_categories = NoteCategory.objects.all()
    note_category = NoteCategory.objects.get(slug=slug)
    note_tags = NoteTag.objects.all()
    articles = Note.objects.filter(category=note_category).order_by("-created_at")
    paginator = Paginator(articles, 6) # Show 9 per page.
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

   
    for category in note_categories:
        category.sub_categories = category.subcategories.all()
    return render(request,"core/categories/note-category.html",{
        "page_obj":page_obj,
        "article_category":note_category,
        "article_categories":note_categories,
        "article_tags":note_tags,
        
    })

@login_required
def note_subcategory(request,cat_slug,subcat_slug):
    note_categories = NoteCategory.objects.all()
    note_subcategory = NoteSubcategory.objects.get(slug=subcat_slug)
    note_tags = NoteTag.objects.all()
    articles = Note.objects.filter(subcategory=note_subcategory).order_by("-created_at")
    paginator = Paginator(articles, 6) # Show 9 per page.
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

   
    for category in note_categories:
        category.sub_categories = category.subcategories.all()
    return render(request,"core/subcategories/note-subcategory.html",{
        "page_obj":page_obj,
        "article_categories":note_categories,
        "article_subcategory":note_subcategory,
        "article_tags":note_tags,
        
    })

@login_required
def note_tag(request,slug):
    article_categories = NoteCategory.objects.all()
    article_tags = NoteTag.objects.all()
    article_tag = NoteTag.objects.get(slug=slug)
    articles = Note.objects.filter(tags=article_tag).order_by("-created_at")
    paginator = Paginator(articles, 6) # Show 9 per page.
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

   
    for category in article_categories:
        category.sub_categories = category.subcategories.all()
    return render(request,"core/tags/note-tags.html",{
        "page_obj":page_obj,
        "article_category":article_category,
        "article_categories":article_categories,
        "article_tag":article_tag,
        "article_tags":article_tags,
        
    })

# CENTRAL POINT

@login_required
def centralpoint_index(request):

    articles = CentralPoint.objects.all().order_by("-created_at")
    paginator = Paginator(articles, 6) # Show 9 per page.
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    article_tags = CentralPointTag.objects.all()

    article_categories = CentralPointCategory.objects.all()
    for category in article_categories:
        category.sub_categories = category.subcategories.all()

    return render(request,"core/view/centralpoint.html",{
        "articles":articles,
        "page_obj":page_obj,
        "article_categories":article_categories,  
        "article_tags":article_tags     
    })

@login_required
def centralpoint_single(request,slug):
    article = CentralPoint.objects.get(slug=slug)
    article_categories = CentralPointCategory.objects.all()
    article_tags = CentralPointTag.objects.all()
    for category in article_categories:
        category.sub_categories = category.subcategories.all()

    return render(request,"core/singles/centralpoint-single.html",{
        "article":article,
        "article_categories":article_categories,
        "article_tags":article_tags,
        
        
    })

@login_required
def centralpoint_category(request,slug):
    article_categories = CentralPointCategory.objects.all()
    article_category = CentralPointCategory.objects.get(slug=slug)
    article_tags = CentralPointTag.objects.all()
    articles = CentralPoint.objects.filter(category=article_category).order_by("-created_at")
    paginator = Paginator(articles, 6) # Show 9 per page.
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

   
    for category in article_categories:
        category.sub_categories = category.subcategories.all()
    return render(request,"core/categories/centralpoint-category.html",{
        "page_obj":page_obj,
        "article_category":article_category,
        "article_categories":article_categories,
        "article_tags":article_tags,
        
    })

@login_required
def centralpoint_subcategory(request,cat_slug,subcat_slug):
    article_categories = CentralPointCategory.objects.all()
    article_subcategory = CentralPointSubcategory.objects.get(slug=subcat_slug)
    article_tags = CentralPointTag.objects.all()
    articles = CentralPoint.objects.filter(subcategory=article_subcategory).order_by("-created_at")
    paginator = Paginator(articles, 6) # Show 9 per page.
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

   
    for category in article_categories:
        category.sub_categories = category.subcategories.all()
    return render(request,"core/subcategories/centralpoint-subcategory.html",{
        "page_obj":page_obj,
        "article_category":article_category,
        "article_categories":article_categories,
        "article_subcategory":article_subcategory,
        "article_tags":article_tags,
        
    })

@login_required
def centralpoint_tag(request,slug):
    article_categories = CentralPointCategory.objects.all()
    article_tags = CentralPointTag.objects.all()
    article_tag = CentralPointTag.objects.get(slug=slug)
    articles = CentralPoint.objects.filter(tags=article_tag).order_by("-created_at")
    paginator = Paginator(articles, 6) # Show 9 per page.
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

   
    for category in article_categories:
        category.sub_categories = category.subcategories.all()
    return render(request,"core/tags/centralpoint-tags.html",{
        "page_obj":page_obj,
        "article_category":article_category,
        "article_categories":article_categories,
        "article_tag":article_tag,
        "article_tags":article_tags,
        
    })

# STRATEGY
@login_required
def strategy_index(request):


    articles = Strategy.objects.all().order_by("-created_at")
    paginator = Paginator(articles, 6) # Show 9 per page.
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    article_tags = StrategyTag.objects.all()

    article_categories = StrategyCategory.objects.all()
    for category in article_categories:
        category.sub_categories = category.subcategories.all()
    
  
  

    return render(request,"core/view/strategy.html",{
        "articles":articles,
        "page_obj":page_obj,
        "article_categories":article_categories,  
        "article_tags":article_tags,
    })
@login_required
def strategy_single(request,slug):
    article = Strategy.objects.get(slug=slug)
    article_categories = StrategyCategory.objects.all()
    article_tags = StrategyTag.objects.all()
    for category in article_categories:
        category.sub_categories = category.subcategories.all()

    return render(request,"core/singles/strategy-single.html",{
        "article":article,
        "article_categories":article_categories,
        "article_tags":article_tags,
        
        
    })
@login_required
def strategy_category(request,slug):

    article_categories = StrategyCategory.objects.all()
    article_category = StrategyCategory.objects.get(slug=slug)
    articles = Strategy.objects.filter(category=article_category).order_by("-created_at")
    paginator = Paginator(articles, 6) # Show 9 per page.
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    article_tags = StrategyTag.objects.all()


    article_categories = StrategyCategory.objects.all()
    for category in article_categories:
        category.sub_categories = category.subcategories.all()

    return render(request,"core/categories/strategy-category.html",{
        "page_obj":page_obj,
        "article_category":article_category,
        "article_categories":article_categories,
        "article_tags":article_tags,
        
    })
@login_required
def strategy_subcategory(request,cat_slug,subcat_slug):
    article_categories = StrategyCategory.objects.all()
    article_subcategory = StrategySubcategory.objects.get(slug=subcat_slug)
    article_tags = StrategyTag.objects.all()
    articles = Strategy.objects.filter(subcategory=article_subcategory).order_by("-created_at")
    paginator = Paginator(articles, 6) # Show 9 per page.
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

   
    for category in article_categories:
        category.sub_categories = category.subcategories.all()
    return render(request,"core/subcategories/strategy-subcategory.html",{
        "page_obj":page_obj,
        "article_category":article_category,
        "article_categories":article_categories,
        "article_subcategory":article_subcategory,
        "article_tags":article_tags,
        
    })
@login_required
def strategy_tag(request,slug):
    article_categories = StrategyCategory.objects.all()
    article_tags = StrategyTag.objects.all()
    article_tag = StrategyTag.objects.get(slug=slug)
    articles = Strategy.objects.filter(tags=article_tag).order_by("-created_at")
    paginator = Paginator(articles, 6) # Show 9 per page.
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

   
    for category in article_categories:
        category.sub_categories = category.subcategories.all()
    return render(request,"core/tags/strategy-tags.html",{
        "page_obj":page_obj,
        "article_category":article_category,
        "article_categories":article_categories,
        "article_tag":article_tag,
        "article_tags":article_tags,
        
    })

# DECISION
@login_required
def decision_index(request):


    articles = Decision.objects.all().order_by("-created_at")
    paginator = Paginator(articles, 6) # Show 9 per page.
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    article_tags = DecisionTag.objects.all()

    article_categories = DecisionCategory.objects.all()
    for category in article_categories:
        category.sub_categories = category.subcategories.all()
    
  
  

    return render(request,"core/view/decision.html",{
        "articles":articles,
        "page_obj":page_obj,
        "article_categories":article_categories,  
        "article_tags":article_tags,
    })
@login_required
def decision_single(request,slug):
    article = Decision.objects.get(slug=slug)
    article_categories = DecisionCategory.objects.all()
    article_tags = DecisionTag.objects.all()
    for category in article_categories:
        category.sub_categories = category.subcategories.all()

    return render(request,"core/singles/decision-single.html",{
        "article":article,
        "article_categories":article_categories,
        "article_tags":article_tags,
        
        
    })
@login_required
def decision_category(request,slug):

    article_categories = DecisionCategory.objects.all()
    article_category = DecisionCategory.objects.get(slug=slug)
    articles = Decision.objects.filter(category=article_category).order_by("-created_at")
    paginator = Paginator(articles, 6) # Show 9 per page.
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    article_tags = DecisionTag.objects.all()


    article_categories = DecisionCategory.objects.all()
    for category in article_categories:
        category.sub_categories = category.subcategories.all()

    return render(request,"core/categories/decision-category.html",{
        "page_obj":page_obj,
        "article_category":article_category,
        "article_categories":article_categories,
        "article_tags":article_tags,
        
    })
@login_required
def decision_subcategory(request,cat_slug,subcat_slug):
    article_categories = DecisionCategory.objects.all()
    article_subcategory = DecisionSubcategory.objects.get(slug=subcat_slug)
    article_tags = DecisionTag.objects.all()
    articles = Decision.objects.filter(subcategory=article_subcategory).order_by("-created_at")
    paginator = Paginator(articles, 6) # Show 9 per page.
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

   
    for category in article_categories:
        category.sub_categories = category.subcategories.all()
    return render(request,"core/subcategories/decision-subcategory.html",{
        "page_obj":page_obj,
        "article_category":article_category,
        "article_categories":article_categories,
        "article_subcategory":article_subcategory,
        "article_tags":article_tags,
        
    })
@login_required
def decision_tag(request,slug):
    article_categories = DecisionCategory.objects.all()
    article_tags = DecisionTag.objects.all()
    article_tag = DecisionTag.objects.get(slug=slug)
    articles = Decision.objects.filter(tags=article_tag).order_by("-created_at")
    paginator = Paginator(articles, 6) # Show 9 per page.
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

   
    for category in article_categories:
        category.sub_categories = category.subcategories.all()
    return render(request,"core/tags/decision-tags.html",{
        "page_obj":page_obj,
        "article_category":article_category,
        "article_categories":article_categories,
        "article_tag":article_tag,
        "article_tags":article_tags,
        
    })

# GOAL
@login_required
def goal_index(request):


    articles = Goal.objects.all().order_by("-created_at")
    paginator = Paginator(articles, 6) # Show 9 per page.
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    article_tags = GoalTag.objects.all()

    article_categories = GoalCategory.objects.all()
    for category in article_categories:
        category.sub_categories = category.subcategories.all()
    
  
  

    return render(request,"core/view/goal.html",{
        "articles":articles,
        "page_obj":page_obj,
        "article_categories":article_categories,  
        "article_tags":article_tags,
    })
@login_required
def goal_single(request,slug):
    article = Goal.objects.get(slug=slug)
    article_categories = GoalCategory.objects.all()
    article_tags = GoalTag.objects.all()
    for category in article_categories:
        category.sub_categories = category.subcategories.all()

    return render(request,"core/singles/goal-single.html",{
        "article":article,
        "article_categories":article_categories,
        "article_tags":article_tags,
        
        
    })
@login_required
def goal_category(request,slug):

    article_categories = GoalCategory.objects.all()
    article_category = GoalCategory.objects.get(slug=slug)
    articles = Goal.objects.filter(category=article_category).order_by("-created_at")
    paginator = Paginator(articles, 6) # Show 9 per page.
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    article_tags = GoalTag.objects.all()


    article_categories = GoalCategory.objects.all()
    for category in article_categories:
        category.sub_categories = category.subcategories.all()

    return render(request,"core/categories/goal-category.html",{
        "page_obj":page_obj,
        "article_category":article_category,
        "article_categories":article_categories,
        "article_tags":article_tags,
        
    })
@login_required
def goal_subcategory(request,cat_slug,subcat_slug):
    article_categories = GoalCategory.objects.all()
    article_subcategory = GoalSubcategory.objects.get(slug=subcat_slug)
    article_tags = GoalTag.objects.all()
    articles = Goal.objects.filter(subcategory=article_subcategory).order_by("-created_at")
    paginator = Paginator(articles, 6) # Show 9 per page.
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

   
    for category in article_categories:
        category.sub_categories = category.subcategories.all()
    return render(request,"core/subcategories/goal-subcategory.html",{
        "page_obj":page_obj,
        "article_category":article_category,
        "article_categories":article_categories,
        "article_subcategory":article_subcategory,
        "article_tags":article_tags,
        
    })
@login_required
def goal_tag(request,slug):
    article_categories = GoalCategory.objects.all()
    article_tags = GoalTag.objects.all()
    article_tag = GoalTag.objects.get(slug=slug)
    articles = Goal.objects.filter(tags=article_tag).order_by("-created_at")
    paginator = Paginator(articles, 6) # Show 9 per page.
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

   
    for category in article_categories:
        category.sub_categories = category.subcategories.all()
    return render(request,"core/tags/goal-tags.html",{
        "page_obj":page_obj,
        "article_category":article_category,
        "article_categories":article_categories,
        "article_tag":article_tag,
        "article_tags":article_tags,
        
    })
