from django.db import models
from django.utils.text import slugify
from django_ckeditor_5.fields import CKEditor5Field
from django.db.models import DateField

# Create your models here.

# BASE CATEGORY AND TAG MODELS
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

# ARTICLE MODELS
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


# JOURNAL MODELS
class JournalCategory(BaseCategory):
    pass

class JournalSubcategory(models.Model):
    category = models.ForeignKey(
        JournalCategory,
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

class JournalTag(BaseTag):
    pass

class Journal(models.Model):
    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    content = CKEditor5Field('Content', config_name='extends')  # or 'default'
    category = models.ForeignKey(
        JournalCategory,
        on_delete=models.CASCADE,
        related_name="journals_by_category",
        null=True
    )
    subcategory = models.ForeignKey(
        JournalSubcategory,
        on_delete=models.CASCADE,
        related_name="journals_by_subcategory",
        blank=True,
        null=True

    )
    tags = models.ManyToManyField(
        JournalTag,
        related_name="journals_by_tag",
        blank=True
    )
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title


# Note Models
class NoteCategory(BaseCategory):
    pass

class NoteSubcategory(models.Model):
    category = models.ForeignKey(
        NoteCategory,
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

class NoteTag(BaseTag):
    pass

class Note(models.Model):
    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    content = CKEditor5Field('Content', config_name='extends')  # or 'default'
    category = models.ForeignKey(
        NoteCategory,
        on_delete=models.CASCADE,
        related_name="notes_by_category",
        null=True
    )
    subcategory = models.ForeignKey(
        NoteSubcategory,
        on_delete=models.CASCADE,
        related_name="notes_by_subcategory",
        blank=True,
        null=True

    )
    tags = models.ManyToManyField(
        NoteTag,
        related_name="notes_by_tag",
        blank=True
    )
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title


# CENTRAL POINT MODELS
class CentralPointCategory(BaseCategory):
    pass

class CentralPointSubcategory(models.Model):
    category = models.ForeignKey(
        CentralPointCategory,
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

class CentralPointTag(BaseTag):
    pass

class CentralPoint(models.Model):
    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    content = CKEditor5Field('Content', config_name='extends')  # or 'default'
    category = models.ForeignKey(
        CentralPointCategory,
        on_delete=models.CASCADE,
        related_name="centralpoints_by_category",
        null=True
    )
    subcategory = models.ForeignKey(
        CentralPointSubcategory,
        on_delete=models.CASCADE,
        related_name="centralpoints_by_subcategory",
        blank=True,
        null=True

    )
    tags = models.ManyToManyField(
        CentralPointTag,
        related_name="centralpoints_by_tag",
        blank=True
    )
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title


# STRATEGY MODELS
class StrategyCategory(BaseCategory):
    pass

class StrategySubcategory(models.Model):
    category = models.ForeignKey(
        StrategyCategory,
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

class StrategyTag(BaseTag):
    pass

class Strategy(models.Model):
    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    strenght = CKEditor5Field('Strenghts', config_name='extends')  # or 'default'
    Weeknesses = CKEditor5Field('Weaknesses', config_name='extends')  # or 'default'
    opportunities = CKEditor5Field('Opportunities', config_name='extends')  # or 'default'
    threats = CKEditor5Field('Threats', config_name='extends')  # or 'default'
    strenghts_advantages = CKEditor5Field('How to take advantage of your strenghts', config_name='extends')  # or 'default'
    weekness_minimization = CKEditor5Field('How to take improve or minimize your weaknesses?', config_name='extends')  # or 'default'
    opportunities_advantages = CKEditor5Field('How to take advantage of your opportunities?', config_name='extends')  # or 'default'
    threats_prevention = CKEditor5Field('How to prevent threats from happening?', config_name='extends')  # or 'default'
    finalized_strategy = CKEditor5Field('What is your finalized Strategy?', config_name='extends')  # or 'default'
    category = models.ForeignKey(
        StrategyCategory,
        on_delete=models.CASCADE,
        related_name="strategies_by_category",
        null=True
    )
    subcategory = models.ForeignKey(
        StrategySubcategory,
        on_delete=models.CASCADE,
        related_name="strategies_by_subcategory",
        blank=True,
        null=True

    )
    tags = models.ManyToManyField(
        StrategyTag,
        related_name="strategies_by_tag",
        blank=True
    )



    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

# DECISION MODELS
class DecisionCategory(BaseCategory):
    pass

class DecisionSubcategory(models.Model):
    category = models.ForeignKey(
        DecisionCategory,
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

class DecisionTag(BaseTag):
    pass

class Decision(models.Model):
    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    bothering = CKEditor5Field('What is bothering me? Gather all the data you can on the situation.', config_name='extends')  # or 'default'
    worst_case = CKEditor5Field('What is the worst case scenario?', config_name='extends')  # or 'default'
    root_cause = CKEditor5Field('What might be the root cause of the problem?', config_name='extends')  # or 'default'
    likely_scenario = CKEditor5Field('What is the likely to happen scenario?', config_name='extends')  # or 'default'
    best_case = CKEditor5Field('What is the best case scenario?', config_name='extends')  # or 'default'
    possible_solutions = CKEditor5Field('What are the possible solutions?', config_name='extends')  # or 'default'
    recommended_solution = CKEditor5Field('Which is the recommended solution?', config_name='extends')  # or 'default'
    category = models.ForeignKey(
        DecisionCategory,
        on_delete=models.CASCADE,
        related_name="decisions_by_category",
        null=True
    )
    subcategory = models.ForeignKey(
        DecisionSubcategory,
        on_delete=models.CASCADE,
        related_name="decisions_by_subcategory",
        blank=True,
        null=True

    )
    tags = models.ManyToManyField(
        DecisionTag,
        related_name="decisions_by_tag",
        blank=True
    )


    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title


# GOAL MODELS
class GoalCategory(BaseCategory):
    pass

class GoalSubcategory(models.Model):
    category = models.ForeignKey(
        GoalCategory,
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

class GoalTag(BaseTag):
    pass

class Goal(models.Model):
    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    outcome = CKEditor5Field('What do I want to accomplish?', config_name='extends')  # or 'default'
    purpose = CKEditor5Field('Why do I want to achieve this goal?', config_name='extends')  # or 'default'
    involved_who = CKEditor5Field('Who is involved in this goal?', config_name='extends')  # or 'default'
    where = CKEditor5Field('Where is this goal to be achieved?', config_name='extends')  # or 'default'
    when_conditions = CKEditor5Field('When do I want to achieve this goal? Specify conditions.', config_name='extends')  # or 'default'
    how_much_many = CKEditor5Field('How much/many?', config_name='extends')  # or 'default'
    progress_indicator = CKEditor5Field('How do I know if I have reached my goal?', config_name='extends')  # or 'default'
    have_resources_missing = CKEditor5Field('Do I have the resources and capabilities to achieve the goal? If not what I am missing?', config_name='extends')  # or 'default'
    before_success = CKEditor5Field('Have others done it successfully before, if yes what strategies have they used to do so?', config_name='extends')  # or 'default'
    why_is_realistic = CKEditor5Field('Is this goal realistic and within reach?', config_name='extends')  # or 'default'
    time_resources_reachable = CKEditor5Field('Is this goal reachable given the time and resources?', config_name='extends')  # or 'default'
    relevance = CKEditor5Field('Is this goal relevant to your other goals, how it can relate?', config_name='extends')  # or 'default'
    deadline = DateField()
    pains_linked = CKEditor5Field('Which pain or pains have a linked?', config_name='extends')  # or 'default'
    pleasures_not_action = CKEditor5Field('What pleasure or pleasures have I gained by not taking action?', config_name='extends')  # or 'default'
    cost_not_action = CKEditor5Field('What will be the cost if I dont change or take action?', config_name='extends')  # or 'default'
    pleasures_action = CKEditor5Field('What pleasures I will gain by following through?', config_name='extends')  # or 'default's
    category = models.ForeignKey(
        GoalCategory,
        on_delete=models.CASCADE,
        related_name="goals_by_category",
        null=True
    )
    subcategory = models.ForeignKey(
        GoalSubcategory,
        on_delete=models.CASCADE,
        related_name="goals_by_subcategory",
        blank=True,
        null=True

    )
    tags = models.ManyToManyField(
        GoalTag,
        related_name="goals_by_tag",
        blank=True
    )

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

