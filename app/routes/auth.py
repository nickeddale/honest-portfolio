from flask import Blueprint, jsonify, redirect, request, url_for, current_app
from flask_login import login_user, logout_user, login_required, current_user
from flask_wtf.csrf import generate_csrf
from app.auth import oauth
from app.auth.auth_service import AuthService

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/auth/google/login')
def google_login():
    """Initiate Google OAuth login."""
    if not current_app.config.get('GOOGLE_CLIENT_ID'):
        return jsonify({'error': 'Google OAuth not configured'}), 500

    redirect_uri = url_for('auth.google_callback', _external=True)
    return oauth.google.authorize_redirect(redirect_uri)


@auth_bp.route('/auth/google/callback')
def google_callback():
    """Handle Google OAuth callback."""
    try:
        token = oauth.google.authorize_access_token()
        user_info = token.get('userinfo')

        if not user_info:
            return redirect('/login.html?error=auth_failed')

        # Authenticate/create user
        provider_info = {
            'provider_user_id': user_info.get('sub'),
            'email': user_info.get('email'),
            'name': user_info.get('name'),
            'profile_picture': user_info.get('picture')
        }

        user = AuthService.authenticate_with_provider('google', provider_info)
        login_user(user, remember=True)

        return redirect('/')
    except Exception as e:
        current_app.logger.error(f"Google OAuth error: {e}")
        return redirect('/login.html?error=auth_failed')


@auth_bp.route('/auth/logout', methods=['POST'])
@login_required
def logout():
    """Logout the current user."""
    logout_user()
    return jsonify({'message': 'Logged out successfully'})


@auth_bp.route('/auth/me')
@login_required
def get_current_user():
    """Get current user's public info."""
    return jsonify(current_user.to_dict_public())


@auth_bp.route('/auth/me/profile')
@login_required
def get_user_profile():
    """Get current user's full profile."""
    return jsonify(current_user.to_dict_profile())


@auth_bp.route('/auth/providers')
def list_providers():
    """List available authentication providers."""
    providers = []

    if current_app.config.get('GOOGLE_CLIENT_ID'):
        providers.append({
            'name': 'google',
            'display_name': 'Google',
            'login_url': '/api/auth/google/login'
        })

    return jsonify({'providers': providers})


@auth_bp.route('/auth/dev-status')
def dev_status():
    """Check if development mode is enabled."""
    return jsonify({
        'dev_mode': current_app.config.get('ENABLE_TEST_AUTH', False)
    })


@auth_bp.route('/csrf-token')
def get_csrf_token():
    """Get CSRF token for frontend."""
    return jsonify({'csrf_token': generate_csrf()})
