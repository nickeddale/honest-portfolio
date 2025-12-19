"""
Premium upgrade routes for Honest Portfolio.
"""

from flask import Blueprint, jsonify
from flask_login import login_required, current_user
from datetime import datetime
from app import db

upgrade_bp = Blueprint('upgrade', __name__)


@upgrade_bp.route('/upgrade', methods=['POST'])
@login_required
def upgrade_to_premium():
    """
    Upgrade the current user to premium status.
    This is a fake payment flow - no actual payment is processed.
    """
    if current_user.is_premium:
        return jsonify({
            'success': True,
            'message': 'You are already a premium member!',
            'user': current_user.to_dict_profile()
        }), 200

    current_user.is_premium = True
    current_user.premium_since = datetime.utcnow()
    db.session.commit()

    return jsonify({
        'success': True,
        'message': 'Welcome to Premium! You now have unlimited access.',
        'user': current_user.to_dict_profile()
    }), 200


@upgrade_bp.route('/premium/status', methods=['GET'])
@login_required
def get_premium_status():
    """Get the current user's premium status."""
    return jsonify({
        'is_premium': current_user.is_premium,
        'premium_since': current_user.premium_since.isoformat() if current_user.premium_since else None,
        'features': {
            'unlimited_pdf_uploads': current_user.is_premium,
            'custom_comparison_stocks': current_user.is_premium
        }
    }), 200
