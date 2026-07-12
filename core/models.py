from django.db import models
from django.utils.text import slugify
from django_ckeditor_5.fields import CKEditor5Field
from django.db.models import DateField

# Create your models here.

# POST TYPE MODEL

# class Category(models.Model):
#     name = models.CharField(max_length=255)
#     slug = models.SlugField(unique=True, blank=True)

#     def save(self, *args, **kwargs):
#         if not self.slug:
#             self.slug = slugify(self.name)
#         super().save(*args, **kwargs)

#     def __str__(self):
#         return self.name

# class Subcategory(models.Model):
    
#     name = models.CharField(max_length=255)
#     slug = models.SlugField(unique=True, blank=True)
#     category = models.ForeignKey(Category,on_delete=models.CASCADE,related_name="subcategories_by_category")

#     def save(self, *args, **kwargs):
#         if not self.slug:
#             self.slug = slugify(self.name)
#         super().save(*args, **kwargs)

#     def __str__(self):
#         return self.name



# class Tag(models.Model):
#     name = models.CharField(max_length=255)
#     slug = models.SlugField(unique=True, blank=True)

#     def save(self, *args, **kwargs):
#         if not self.slug:
#             self.slug = slugify(self.name)
#         super().save(*args, **kwargs)

#     def __str__(self):
#         return self.name
class BaseCategory(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, blank=True)

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class BaseTag(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, blank=True)

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class ArticleCategory(BaseCategory):
    pass

class ArticleSubcategory(models.Model):
    category = models.ForeignKey(
        ArticleCategory,
        on_delete=models.CASCADE,
        related_name="subcategories"
    )
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.category.name} / {self.name}"




class ArticleTag(BaseTag):
    pass


class JournalCategory(BaseCategory):
    pass


class JournalTag(BaseTag):
    pass


class NoteCategory(BaseCategory):
    pass


class NoteTag(BaseTag):
    pass


class CentralPointCategory(BaseCategory):
    pass


class CentralPointTag(BaseTag):
    pass


class StrategyCategory(BaseCategory):
    pass


class StrategyTag(BaseTag):
    pass


class DecisionCategory(BaseCategory):
    pass


class DecisionTag(BaseTag):
    pass


class GoalCategory(BaseCategory):
    pass


class GoalTag(BaseTag):
    pass

class Article(models.Model):
    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    content = CKEditor5Field('Content', config_name='extends')  # or 'default'
    category = models.ForeignKey(
        ArticleCategory,
        on_delete=models.CASCADE,
        related_name="articles"
    )
    subcategory = models.ForeignKey(
        ArticleSubcategory,
        on_delete=models.CASCADE,
        related_name="articles",
        blank=True,
        null=True

    )
    tags = models.ManyToManyField(
        ArticleTag,
        related_name="articles",
        blank=True
    )
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

class Journal(models.Model):
    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    content = CKEditor5Field('Content', config_name='extends')  # or 'default'
    # category = models.ForeignKey(Category,on_delete=models.CASCADE,related_name="journals_by_category")
    # tag = models.ForeignKey(Tag,on_delete=models.CASCADE,related_name="journals_by_tags")
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title


class Note(models.Model):
    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    content = CKEditor5Field('Content', config_name='extends')  # or 'default'
    # category = models.ForeignKey(Category,on_delete=models.CASCADE,related_name="notes_by_category")
    # tag = models.ForeignKey(Tag,on_delete=models.CASCADE,related_name="notes_by_tags")
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

class CentralPoint(models.Model):
    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    content = CKEditor5Field('Content', config_name='extends')  # or 'default'
    # category = models.ForeignKey(Category,on_delete=models.CASCADE,related_name="centralpoints_by_category")
    # tag = models.ForeignKey(Tag,on_delete=models.CASCADE,related_name="centralpoints_by_tags")
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

class Strategy(models.Model):
    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    strenght = CKEditor5Field('Content', config_name='extends')  # or 'default'
    # category = models.ForeignKey(Category,on_delete=models.CASCADE,related_name="staregies_by_category")
    # tag = models.ForeignKey(Tag,on_delete=models.CASCADE,related_name="strategies_by_tags")
    Weeknesses = CKEditor5Field('Content', config_name='extends')  # or 'default'
    opportunities = CKEditor5Field('Content', config_name='extends')  # or 'default'
    threats = CKEditor5Field('Content', config_name='extends')  # or 'default'
    strenghts_advantages = CKEditor5Field('Content', config_name='extends')  # or 'default'
    weekness_minimization = CKEditor5Field('Content', config_name='extends')  # or 'default'
    opportunities_advantages = CKEditor5Field('Content', config_name='extends')  # or 'default'
    threats_prevention = CKEditor5Field('Content', config_name='extends')  # or 'default'
    finalized_strategy = CKEditor5Field('Content', config_name='extends')  # or 'default'

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

class Decision(models.Model):
    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    bothering = CKEditor5Field('Content', config_name='extends')  # or 'default'
    worst_case = CKEditor5Field('Content', config_name='extends')  # or 'default'
    root_cause = CKEditor5Field('Content', config_name='extends')  # or 'default'
    likely_scenario = CKEditor5Field('Content', config_name='extends')  # or 'default'
    best_case = CKEditor5Field('Content', config_name='extends')  # or 'default'
    possible_solutions = CKEditor5Field('Content', config_name='extends')  # or 'default'
    recommended_solution = CKEditor5Field('Content', config_name='extends')  # or 'default'
    # category = models.ForeignKey(Category,on_delete=models.CASCADE,related_name="decisions_by_category")
    # tag = models.ForeignKey(Tag,on_delete=models.CASCADE,related_name="decisions_by_tags")
    

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title


class Goal(models.Model):
    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    outcome = CKEditor5Field('Content', config_name='extends')  # or 'default'
    purpose = CKEditor5Field('Content', config_name='extends')  # or 'default'
    involved_who = CKEditor5Field('Content', config_name='extends')  # or 'default'
    where = CKEditor5Field('Content', config_name='extends')  # or 'default'
    when_conditions = CKEditor5Field('Content', config_name='extends')  # or 'default'
    how_much_many = CKEditor5Field('Content', config_name='extends')  # or 'default'
    progress_indicator = CKEditor5Field('Content', config_name='extends')  # or 'default'
    have_resources_missing = CKEditor5Field('Content', config_name='extends')  # or 'default'
    before_success = CKEditor5Field('Content', config_name='extends')  # or 'default'
    why_is_realistic = CKEditor5Field('Content', config_name='extends')  # or 'default'
    time_resources_reachable = CKEditor5Field('Content', config_name='extends')  # or 'default'
    relevance = CKEditor5Field('Content', config_name='extends')  # or 'default'
    deadline = DateField()
    pains_linked = CKEditor5Field('Content', config_name='extends')  # or 'default'
    pleasures_not_action = CKEditor5Field('Content', config_name='extends')  # or 'default'
    cost_not_action = CKEditor5Field('Content', config_name='extends')  # or 'default'
    pleasures_action = CKEditor5Field('Content', config_name='extends')  # or 'default's
    # category = models.ForeignKey(Category,on_delete=models.CASCADE,related_name="goals_by_category")
    # tag = models.ForeignKey(Tag,on_delete=models.CASCADE,related_name="goals_by_tags")


