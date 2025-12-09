from flask import Blueprint, jsonify
from app.services.stock_data import validate_ticker
from app.models import ComparisonStock

stocks_bp = Blueprint('stocks', __name__)

@stocks_bp.route('/stock/validate/<ticker>', methods=['GET'])
def validate_stock(ticker):
    ticker = ticker.upper()
    is_valid = validate_ticker(ticker)
    return jsonify({'ticker': ticker, 'valid': is_valid})

@stocks_bp.route('/comparison-stocks', methods=['GET'])
def get_comparison_stocks():
    stocks = ComparisonStock.query.filter_by(is_default=True).all()
    return jsonify([s.to_dict() for s in stocks])
