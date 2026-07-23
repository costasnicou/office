import json
import secrets
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"


class GoogleOAuthError(Exception):
    """Raised when Google OAuth cannot be completed safely."""


def _credentials():
    client_id = getattr(settings, "GOOGLE_OAUTH_CLIENT_ID", "")
    client_secret = getattr(settings, "GOOGLE_OAUTH_CLIENT_SECRET", "")
    if not client_id or not client_secret:
        raise ImproperlyConfigured(
            "Set GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET."
        )
    return client_id, client_secret


def authorization_url(request, callback_url):
    client_id, _ = _credentials()
    state = secrets.token_urlsafe(32)
    request.session["google_oauth_state"] = state
    query = urlencode({
        "client_id": client_id,
        "redirect_uri": callback_url,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "prompt": "select_account",
    })
    return f"{AUTHORIZE_URL}?{query}"


def fetch_profile(code, callback_url):
    client_id, client_secret = _credentials()
    token_data = _request_json(
        TOKEN_URL,
        data=urlencode({
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": callback_url,
            "grant_type": "authorization_code",
        }).encode(),
    )
    access_token = token_data.get("access_token")
    if not access_token:
        raise GoogleOAuthError("Google did not return an access token.")

    profile = _request_json(
        USERINFO_URL,
        headers={"Authorization": f"Bearer {access_token}"},
    )
    if not profile.get("email") or not profile.get("email_verified"):
        raise GoogleOAuthError("Google did not return a verified email address.")
    return profile


def _request_json(url, data=None, headers=None):
    request = Request(url, data=data, headers=headers or {}, method="POST" if data else "GET")
    if data:
        request.add_header("Content-Type", "application/x-www-form-urlencoded")
    try:
        with urlopen(request, timeout=10) as response:
            return json.loads(response.read().decode())
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise GoogleOAuthError("Google authentication is temporarily unavailable.") from exc
