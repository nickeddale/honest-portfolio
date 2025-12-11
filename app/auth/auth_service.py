from datetime import datetime
from app import db
from app.models import User, UserAuthAccount


class AuthService:
    """Service for handling user authentication and account management."""

    @staticmethod
    def authenticate_with_provider(provider_name: str, user_info: dict) -> User:
        """
        Authenticate or create user from OAuth provider data.

        Args:
            provider_name: Name of the OAuth provider (e.g., 'google', 'test')
            user_info: Dict containing provider_user_id, email, name, profile_picture

        Returns:
            User instance
        """
        # Look for existing auth account
        account = UserAuthAccount.query.filter_by(
            provider=provider_name,
            provider_user_id=user_info['provider_user_id']
        ).first()

        if account:
            # Existing user - update last_used_at
            account.last_used_at = datetime.utcnow()
            user = account.user
            user.last_login = datetime.utcnow()

            # Update profile info if changed
            if user_info.get('name'):
                user.name = user_info['name']
            if user_info.get('profile_picture'):
                user.profile_picture = user_info['profile_picture']
        else:
            # Check if user with this email already exists (for account linking)
            user = None
            if user_info.get('email'):
                user = User.query.filter_by(email=user_info['email']).first()

            if user:
                # Link new provider to existing user
                account = AuthService._create_auth_account(user, provider_name, user_info)
            else:
                # Create new user and auth account
                user = AuthService._create_user(user_info)
                account = AuthService._create_auth_account(user, provider_name, user_info)

        db.session.commit()
        return user

    @staticmethod
    def _create_user(user_info: dict) -> User:
        """Create a new user from provider info."""
        user = User(
            email=user_info.get('email'),
            name=user_info.get('name', 'User'),
            profile_picture=user_info.get('profile_picture'),
            created_at=datetime.utcnow(),
            last_login=datetime.utcnow()
        )
        db.session.add(user)
        db.session.flush()  # Get the user.id
        return user

    @staticmethod
    def _create_auth_account(user: User, provider_name: str, user_info: dict) -> UserAuthAccount:
        """Create a new auth account for a user."""
        account = UserAuthAccount(
            user_id=user.id,
            provider=provider_name,
            provider_user_id=user_info['provider_user_id'],
            email=user_info.get('email'),
            created_at=datetime.utcnow(),
            last_used_at=datetime.utcnow()
        )
        db.session.add(account)
        return account
