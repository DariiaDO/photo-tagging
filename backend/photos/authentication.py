import hmac

from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from rest_framework import authentication
from rest_framework.exceptions import AuthenticationFailed


class OptionalBearerTokenAuthentication(authentication.BaseAuthentication):
    """Protect API endpoints with a shared bearer token when configured."""

    keyword = "Bearer"

    def authenticate(self, request):
        expected_token = str(getattr(settings, "PHOTO_API_AUTH_TOKEN", "") or "").strip()
        if not expected_token:
            return None

        auth_header = authentication.get_authorization_header(request).decode("utf-8")
        if not auth_header:
            raise AuthenticationFailed("Authentication token is missing.")

        try:
            keyword, token = auth_header.split(None, 1)
        except ValueError as exc:
            raise AuthenticationFailed("Invalid Authorization header.") from exc

        if keyword.lower() != self.keyword.lower():
            raise AuthenticationFailed("Invalid Authorization scheme.")

        if not hmac.compare_digest(token.strip(), expected_token):
            raise AuthenticationFailed("Invalid authentication token.")

        return (AnonymousUser(), token)
