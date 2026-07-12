from django.urls import path
from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("article/<slug:slug>",views.article_single,name="article_single"),

]