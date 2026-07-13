from django.urls import path
from . import views

urlpatterns = [

    # articles
    path("", views.index, name="index"),
    path("article/<slug:slug>",views.article_single,name="article_single"),
    path("articles/category/<slug:slug>",views.article_category,name="article_category"),
    path("article/category/<slug:cat_slug>/<slug:subcat_slug>",views.article_subcategory,name="article_subcategory"),
    path("article/tag/<slug:slug>",views.article_tag,name="article_tag"),

    # journal
    path("journals/",views.journal_index,name="journal_index"),
    path("journal/<slug:slug>",views.journal_single,name="journal_single"),
    path("journals/category/<slug:slug>",views.journal_category,name="journal_category"),
    path("journals/category/<slug:cat_slug>/<slug:subcat_slug>",views.journal_subcategory,name="journal_subcategory"),
    path("journals/tag/<slug:slug>",views.journal_tag,name="journal_tag"),

    # note
    path("notes/",views.note_index,name="note_index"),
    path("note/<slug:slug>",views.note_single,name="note_single"),
    path("notes/category/<slug:slug>",views.note_category,name="note_category"),
    path("notes/category/<slug:cat_slug>/<slug:subcat_slug>",views.note_subcategory,name="note_subcategory"),
    path("notes/tag/<slug:slug>",views.note_tag,name="note_tag"),

    # cental point
    path("centralpoints/",views.centralpoint_index,name="centralpoint_index"),
    path("centralpoint/<slug:slug>",views.centralpoint_single,name="centralpoint_single"),
    path("centralpoints/category/<slug:slug>",views.centralpoint_category,name="centralpoint_category"),
    path("centralpoints/category/<slug:cat_slug>/<slug:subcat_slug>",views.centralpoint_subcategory,name="centralpoint_subcategory"),
    path("centralpoints/tag/<slug:slug>",views.centralpoint_tag,name="centralpoint_tag"),

    # strategy
    path("strategies/",views.strategy_index,name="strategy_index"),
    path("strategy/<slug:slug>",views.strategy_single,name="strategy_single"),
    path("strategies/category/<slug:slug>",views.strategy_category,name="strategy_category"),
    path("strategies/category/<slug:cat_slug>/<slug:subcat_slug>",views.strategy_subcategory,name="strategy_subcategory"),
    path("strategies/tag/<slug:slug>",views.strategy_tag,name="strategy_tag"),

]