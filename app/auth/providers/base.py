from abc import ABC, abstractmethod
from typing import Dict, Optional


class AuthProvider(ABC):
    """Abstract base class for authentication providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the provider name (e.g., 'google')."""
        pass

    @abstractmethod
    def get_authorization_url(self, redirect_uri: str) -> str:
        """
        Get the authorization URL to redirect user to.

        Args:
            redirect_uri: The callback URL after authorization

        Returns:
            Authorization URL string
        """
        pass

    @abstractmethod
    def handle_callback(self) -> Optional[Dict]:
        """
        Handle the OAuth callback and extract user info.

        Returns:
            Dict with keys: provider_user_id, email, name, profile_picture
            Or None if authentication failed
        """
        pass
