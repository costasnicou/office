from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q


class UsernameOrEmailBackend(ModelBackend):
    """Authenticate local users with either their username or email address."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        identifier = username or kwargs.get("email")
        if not identifier or password is None:
            return None

        user_model = get_user_model()
        matches = list(
            user_model._default_manager.filter(
                Q(username=identifier) | Q(email__iexact=identifier)
            )[:2]
        )
        if len(matches) != 1:
            # Keep password checking time less distinguishable for unknown users.
            user_model().set_password(password)
            return None

        user = matches[0]
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
