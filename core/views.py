from django.shortcuts import render
from django.core.paginator import Paginator
from .models import *
# Create your views here.
def index(request):

    articles = Article.objects.all().order_by("-created_at")
    paginator = Paginator(articles, 6) # Show 9 per page.
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    article_categories = ArticleCategory.objects.all()
    for category in article_categories:
        category.sub_categories = category.subcategories.all()

    return render(request,"core/index.html",{
        "articles":articles,
        "page_obj":page_obj,
        "article_categories":article_categories,       
    })

def article_single(request,slug):
    article = Article.objects.get(slug=slug)
    article_categories = ArticleCategory.objects.all()
    for category in article_categories:
        category.sub_categories = category.subcategories.all()

    return render(request,"core/article-single.html",{
        "article":article,
        "article_categories":article_categories,
        
    })

