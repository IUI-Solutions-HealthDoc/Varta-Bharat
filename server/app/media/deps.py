"""Authentication for media and moderation routes: the real bearer-token dependency."""

from app.auth.dependencies import AuthUser, current_user

__all__ = ["AuthUser", "current_user"]