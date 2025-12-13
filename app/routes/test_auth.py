from flask import Blueprint, jsonify, current_app
from flask_login import login_user, logout_user, current_user
from app.auth.auth_service import AuthService
from app import db
from app.models import Purchase

test_auth_bp = Blueprint('test_auth', __name__)


@test_auth_bp.route('/test/auth/create-test-user', methods=['POST'])
def create_test_user():
    """
    Create a test user and log them in.
    Only available when ENABLE_TEST_AUTH is True.
    """
    if not current_app.config.get('ENABLE_TEST_AUTH'):
        return jsonify({'error': 'Test authentication is disabled'}), 403

    # Create or get test user
    user_info = {
        'provider_user_id': 'test-user-001',
        'email': 'test@example.com',
        'name': 'Test User',
        'profile_picture': None
    }

    user = AuthService.authenticate_with_provider('test', user_info)
    login_user(user, remember=True)

    return jsonify({
        'message': 'Test user created and logged in',
        'user': user.to_dict_public()
    })


@test_auth_bp.route('/test/logout', methods=['POST'])
def test_logout():
    """Force logout - only available in dev mode."""
    if not current_app.config.get('ENABLE_TEST_AUTH'):
        return jsonify({'error': 'Test authentication is disabled'}), 403

    logout_user()
    return jsonify({'message': 'Logged out'})


@test_auth_bp.route('/test/auth/clear-purchases', methods=['POST'])
def clear_test_purchases():
    """
    Clear all purchases for the current test user.
    Only available when ENABLE_TEST_AUTH is True.
    """
    if not current_app.config.get('ENABLE_TEST_AUTH'):
        return jsonify({'error': 'Test authentication is disabled'}), 403

    if not current_user.is_authenticated:
        return jsonify({'error': 'Not authenticated'}), 401

    # Delete all purchases for the current user
    deleted_count = Purchase.query.filter_by(user_id=current_user.id).delete()
    db.session.commit()

    return jsonify({
        'message': f'Cleared {deleted_count} purchases',
        'count': deleted_count
    })
