from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver

from .taxonomy import ensure_default_categories


@receiver(user_logged_in)
def create_default_categories_on_sign_in(sender, user, request, **kwargs):
    ensure_default_categories(user)
