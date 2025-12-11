from typing import Dict, Optional
from flask import url_for
from .base import AuthProvider
from app.auth import oauth


class GoogleAuthProvider(AuthProvider):
    """Google OAuth 2.0 authentication provider."""

    @property
    def name(self) -> str:
        return 'google'

    def get_authorization_url(self, redirect_uri: str) -> str:
        """Redirect to Google's authorization endpoint."""
        return oauth.google.authorize_redirect(redirect_uri)

    def handle_callback(self) -> Optional[Dict]:
        """
        Handle Google OAuth callback.

        Returns:
            User info dict or None if failed
        """
        try:
            token = oauth.google.authorize_access_token()
            user_info = token.get('userinfo')

            if not user_info:
                return None

            return {
                'provider_user_id': user_info.get('sub'),
                'email': user_info.get('email'),
                'name': user_info.get('name'),
                'profile_picture': user_info.get('picture')
            }
        except Exception as e:
            print(f"Google OAuth error: {e}")
            return None
