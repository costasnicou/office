from django.urls import path
from . import views

urlpatterns = [

    path("login", views.login_view, name="login"),
    path("register/", views.register_view, name="register"),
    path("auth/google/", views.google_login, name="google_login"),
    path("auth/google/callback/", views.google_callback, name="google_callback"),
    path("logout", views.logout_view, name="logout"),
    path("search/", views.record_search, name="record_search"),

    # articles
    path("", views.index, name="index"),
    path("article/<slug:slug>",views.article_single,name="article_single"),
    path("articles/category/<slug:slug>",views.article_category,name="article_category"),
    path("article/category/<slug:cat_slug>/<slug:subcat_slug>",views.article_subcategory,name="article_subcategory"),
    path("article/tag/<slug:slug>",views.article_tag,name="article_tag"),
    path("articles/add/", views.record_create, {"record_type": "article"}, name="article_create"),
    path("articles/<slug:slug>/edit/", views.record_update, {"record_type": "article"}, name="article_edit"),

    # journal
    path("journals/",views.journal_index,name="journal_index"),
    path("journal/<slug:slug>",views.journal_single,name="journal_single"),
    path("journals/category/<slug:slug>",views.journal_category,name="journal_category"),
    path("journals/category/<slug:cat_slug>/<slug:subcat_slug>",views.journal_subcategory,name="journal_subcategory"),
    path("journals/tag/<slug:slug>",views.journal_tag,name="journal_tag"),
    path("journals/add/", views.record_create, {"record_type": "journal"}, name="journal_create"),
    path("journals/<slug:slug>/edit/", views.record_update, {"record_type": "journal"}, name="journal_edit"),

    # note
    path("notes/",views.note_index,name="note_index"),
    path("note/<slug:slug>",views.note_single,name="note_single"),
    path("notes/category/<slug:slug>",views.note_category,name="note_category"),
    path("notes/category/<slug:cat_slug>/<slug:subcat_slug>",views.note_subcategory,name="note_subcategory"),
    path("notes/tag/<slug:slug>",views.note_tag,name="note_tag"),
    path("notes/add/", views.record_create, {"record_type": "note"}, name="note_create"),
    path("notes/<slug:slug>/edit/", views.record_update, {"record_type": "note"}, name="note_edit"),

    # cental point
    path("centralpoints/",views.centralpoint_index,name="centralpoint_index"),
    path("centralpoint/<slug:slug>",views.centralpoint_single,name="centralpoint_single"),
    path("centralpoints/category/<slug:slug>",views.centralpoint_category,name="centralpoint_category"),
    path("centralpoints/category/<slug:cat_slug>/<slug:subcat_slug>",views.centralpoint_subcategory,name="centralpoint_subcategory"),
    path("centralpoints/tag/<slug:slug>",views.centralpoint_tag,name="centralpoint_tag"),
    path("centralpoints/add/", views.record_create, {"record_type": "centralpoint"}, name="centralpoint_create"),
    path("centralpoints/<slug:slug>/edit/", views.record_update, {"record_type": "centralpoint"}, name="centralpoint_edit"),

    # strategy
    path("strategies/",views.strategy_index,name="strategy_index"),
    path("strategy/<slug:slug>",views.strategy_single,name="strategy_single"),
    path("strategies/category/<slug:slug>",views.strategy_category,name="strategy_category"),
    path("strategies/category/<slug:cat_slug>/<slug:subcat_slug>",views.strategy_subcategory,name="strategy_subcategory"),
    path("strategies/tag/<slug:slug>",views.strategy_tag,name="strategy_tag"),
    path("strategies/add/", views.record_create, {"record_type": "strategy"}, name="strategy_create"),
    path("strategies/<slug:slug>/edit/", views.record_update, {"record_type": "strategy"}, name="strategy_edit"),


    # decision
    path("decisions/",views.decision_index,name="decision_index"),
    path("decision/<slug:slug>",views.decision_single,name="decision_single"),
    path("decisions/category/<slug:slug>",views.decision_category,name="decision_category"),
    path("decisions/category/<slug:cat_slug>/<slug:subcat_slug>",views.decision_subcategory,name="decision_subcategory"),
    path("decisions/tag/<slug:slug>",views.decision_tag,name="decision_tag"),
    path("decisions/add/", views.record_create, {"record_type": "decision"}, name="decision_create"),
    path("decisions/<slug:slug>/edit/", views.record_update, {"record_type": "decision"}, name="decision_edit"),


    # goals
    path("goals/",views.goal_index,name="goal_index"),
    path("goal/<slug:slug>",views.goal_single,name="goal_single"),
    path("goals/category/<slug:slug>",views.goal_category,name="goal_category"),
    path("goals/category/<slug:cat_slug>/<slug:subcat_slug>",views.goal_subcategory,name="goal_subcategory"),
    path("goals/tag/<slug:slug>",views.goal_tag,name="goal_tag"),
    path("goals/add/", views.record_create, {"record_type": "goal"}, name="goal_create"),
    path("goals/<slug:slug>/edit/", views.record_update, {"record_type": "goal"}, name="goal_edit"),

]
