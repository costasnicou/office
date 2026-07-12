from django.urls import path
from . import views

urlpatterns = [

    # articles
    path("", views.index, name="index"),
    path("article/<slug:slug>",views.article_single,name="article_single"),
    path("article/category/<slug:slug>",views.article_category,name="article_category"),
    path("article/category/<slug:cat_slug>/<slug:subcat_slug>",views.article_subcategory,name="article_subcategory"),
    path("article/tag/<slug:slug>",views.article_tag,name="article_tag"),

    # journal
    path("journal/",views.journal_index,name="journal_index"),
    path("journal/<slug:slug>",views.journal_single,name="journal_single"),
    path("journal/category/<slug:slug>",views.journal_category,name="journal_category"),
    path("journal/category/<slug:cat_slug>/<slug:subcat_slug>",views.journal_subcategory,name="journal_subcategory"),
    path("journal/tag/<slug:slug>",views.journal_tag,name="journal_tag"),

    # note
    path("note/",views.note_index,name="note_index"),
    path("note/<slug:slug>",views.note_single,name="note_single"),
    path("note/category/<slug:slug>",views.note_category,name="note_category"),
    path("note/category/<slug:cat_slug>/<slug:subcat_slug>",views.note_subcategory,name="note_subcategory"),
    path("note/tag/<slug:slug>",views.note_tag,name="note_tag"),

    # cental point
    path("centralpoint/",views.centralpoint_index,name="centralpoint_index"),
    path("centralpoint/<slug:slug>",views.centralpoint_single,name="centralpoint_single"),
    path("centralpoint/category/<slug:slug>",views.centralpoint_category,name="centralpoint_category"),
    path("centralpoint/category/<slug:cat_slug>/<slug:subcat_slug>",views.centralpoint_subcategory,name="centralpoint_subcategory"),
    path("centralpoint/tag/<slug:slug>",views.centralpoint_tag,name="centralpoint_tag"),

]