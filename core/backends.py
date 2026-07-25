from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


class UsernameOrEmailBackend(ModelBackend):
    """Authenticate local users with either their username or email address."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        identifier = username or kwargs.get("email")
        if not identifier or password is None:
            return None

        user_model = get_user_model()
        if "@" in identifier:
            matches = user_model._default_manager.filter(email__iexact=identifier)
            # Never guess which account to use if legacy duplicate emails exist.
            if matches.count() != 1:
                user_model().set_password(password)
                return None
            user = matches.first()
            if user.check_password(password) and self.user_can_authenticate(user):
                return user
            return None

        return super().authenticate(
            request,
            username=identifier,
            password=password,
            **kwargs,
        )
