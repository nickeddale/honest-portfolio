from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import Sale, Purchase
from app.services.sale_service import (
    create_sale_with_fifo,
    link_sale_to_reinvestment,
    preview_fifo_assignment,
    InsufficientSharesError
)
from app.services.stock_data import validate_ticker, is_trading_day, get_price_on_date, invalidate_price_cache
from datetime import datetime

sales_bp = Blueprint('sales', __name__)


@sales_bp.route('/sales', methods=['GET'])
@login_required
def get_sales():
    """Get all sales for the current user."""
    sales = Sale.query.filter_by(user_id=current_user.id).order_by(Sale.sale_date.desc()).all()
    return jsonify([s.to_dict() for s in sales])


@sales_bp.route('/sales', methods=['POST'])
@login_required
def create_sale():
    """Create a new sale with FIFO assignment for the current user."""
    data = request.get_json()

    # Validate required fields
    required_fields = ['ticker', 'sale_date', 'shares_sold', 'price_at_sale']
    if not all(k in data for k in required_fields):
        return jsonify({'error': f'Missing required fields: {", ".join(required_fields)}'}), 400

    ticker = data['ticker'].upper()

    # Parse and validate sale_date
    try:
        sale_date = datetime.strptime(data['sale_date'], '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400

    # Validate shares_sold
    try:
        shares_sold = float(data['shares_sold'])
    except (ValueError, TypeError):
        return jsonify({'error': 'shares_sold must be a valid number'}), 400

    if shares_sold <= 0:
        return jsonify({'error': 'shares_sold must be positive'}), 400

    # Validate price_at_sale
    try:
        price_at_sale = float(data['price_at_sale'])
    except (ValueError, TypeError):
        return jsonify({'error': 'price_at_sale must be a valid number'}), 400

    if price_at_sale <= 0:
        return jsonify({'error': 'price_at_sale must be positive'}), 400

    # Validate ticker
    if not validate_ticker(ticker):
        return jsonify({'error': f'Invalid ticker symbol: {ticker}'}), 400

    # Check if it's a trading day
    if not is_trading_day(sale_date):
        return jsonify({'error': 'Sale date must be a valid trading day (not weekend or holiday)'}), 400

    # Create the sale with FIFO assignment
    try:
        sale = create_sale_with_fifo(
            user_id=current_user.id,
            ticker=ticker,
            sale_date=sale_date,
            shares_sold=shares_sold,
            price_at_sale=price_at_sale
        )
    except InsufficientSharesError as e:
        return jsonify({'error': str(e)}), 400
    except ValueError as e:
        return jsonify({'error': str(e)}), 400

    # Handle reinvestment if specified
    reinvest_ticker = data.get('reinvest_ticker')
    reinvest_amount = data.get('reinvest_amount')

    if reinvest_ticker and reinvest_amount:
        reinvest_ticker = reinvest_ticker.upper()

        # Validate reinvestment amount
        try:
            reinvest_amount = float(reinvest_amount)
        except (ValueError, TypeError):
            return jsonify({'error': 'reinvest_amount must be a valid number'}), 400

        if reinvest_amount <= 0:
            return jsonify({'error': 'reinvest_amount must be positive'}), 400

        if reinvest_amount > sale.total_proceeds:
            return jsonify({'error': 'reinvest_amount cannot exceed sale proceeds'}), 400

        # Validate reinvestment ticker
        if not validate_ticker(reinvest_ticker):
            return jsonify({'error': f'Invalid reinvestment ticker symbol: {reinvest_ticker}'}), 400

        # Get price on sale date for reinvestment ticker
        reinvest_price = get_price_on_date(reinvest_ticker, sale_date)
        if reinvest_price is None:
            return jsonify({'error': f'Unable to fetch price for {reinvest_ticker} on {sale_date}'}), 500

        # Calculate shares for reinvestment
        reinvest_shares = reinvest_amount / reinvest_price

        # Create reinvestment purchase
        reinvestment_purchase = Purchase(
            user_id=current_user.id,
            ticker=reinvest_ticker,
            purchase_date=sale_date,
            amount=reinvest_amount,
            shares_bought=reinvest_shares,
            price_at_purchase=reinvest_price
        )
        db.session.add(reinvestment_purchase)
        db.session.flush()

        # Link sale to reinvestment
        try:
            link_sale_to_reinvestment(sale.id, reinvestment_purchase.id, reinvest_amount)
        except ValueError as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 400

    # Invalidate price cache to ensure fresh prices on next fetch
    invalidate_price_cache()

    return jsonify(sale.to_dict()), 201


@sales_bp.route('/sales/<int:id>', methods=['DELETE'])
@login_required
def delete_sale(id):
    """Delete a sale (must belong to current user)."""
    sale = Sale.query.filter_by(id=id, user_id=current_user.id).first()
    if not sale:
        return jsonify({'error': 'Sale not found'}), 404

    db.session.delete(sale)
    db.session.commit()

    # Invalidate price cache to ensure fresh prices on next fetch
    invalidate_price_cache()

    return jsonify({'message': 'Sale deleted'}), 200


@sales_bp.route('/sales/preview', methods=['GET'])
@login_required
def preview_sale():
    """Preview FIFO assignment for a potential sale."""
    ticker = request.args.get('ticker')
    shares_sold = request.args.get('shares_sold')

    # Validate required parameters
    if not ticker or not shares_sold:
        return jsonify({'error': 'Missing required parameters: ticker, shares_sold'}), 400

    ticker = ticker.upper()

    # Validate shares_sold
    try:
        shares_sold = float(shares_sold)
    except (ValueError, TypeError):
        return jsonify({'error': 'shares_sold must be a valid number'}), 400

    if shares_sold <= 0:
        return jsonify({'error': 'shares_sold must be positive'}), 400

    # Get preview
    try:
        preview_data = preview_fifo_assignment(
            user_id=current_user.id,
            ticker=ticker,
            shares_to_sell=shares_sold
        )
    except ValueError as e:
        return jsonify({'error': str(e)}), 400

    return jsonify(preview_data), 200
