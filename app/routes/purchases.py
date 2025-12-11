from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import Purchase, ComparisonStock
from app.services.stock_data import validate_ticker, is_trading_day, get_price_on_date, get_current_price, get_price_history, invalidate_price_cache
from datetime import datetime

purchases_bp = Blueprint('purchases', __name__)


@purchases_bp.route('/purchases', methods=['GET'])
@login_required
def get_purchases():
    """Get all purchases for the current user."""
    purchases = Purchase.query.filter_by(user_id=current_user.id).order_by(Purchase.purchase_date.desc()).all()
    return jsonify([p.to_dict() for p in purchases])


@purchases_bp.route('/purchases', methods=['POST'])
@login_required
def create_purchase():
    """Create a new purchase for the current user."""
    data = request.get_json()

    # Get entry mode, defaulting to 'quick' for backward compatibility
    entry_mode = data.get('entry_mode', 'quick')

    # Validate required fields (ticker and purchase_date are always required)
    if not all(k in data for k in ['ticker', 'purchase_date']):
        return jsonify({'error': 'Missing required fields: ticker, purchase_date'}), 400

    ticker = data['ticker'].upper()
    try:
        purchase_date = datetime.strptime(data['purchase_date'], '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400

    # Validate ticker
    if not validate_ticker(ticker):
        return jsonify({'error': f'Invalid ticker symbol: {ticker}'}), 400

    # Check if it's a trading day
    if not is_trading_day(purchase_date):
        return jsonify({'error': 'Purchase date must be a valid trading day (not weekend or holiday)'}), 400

    # Handle entry mode logic
    if entry_mode == 'detailed':
        # Detailed mode: require quantity and price_per_share
        if not all(k in data for k in ['quantity', 'price_per_share']):
            return jsonify({'error': 'Missing required fields for detailed mode: quantity, price_per_share'}), 400

        try:
            quantity = float(data['quantity'])
        except (ValueError, TypeError):
            return jsonify({'error': 'quantity must be a valid number'}), 400

        try:
            price_per_share = float(data['price_per_share'])
        except (ValueError, TypeError):
            return jsonify({'error': 'price_per_share must be a valid number'}), 400

        if quantity <= 0:
            return jsonify({'error': 'quantity must be positive'}), 400

        if price_per_share <= 0:
            return jsonify({'error': 'price_per_share must be positive'}), 400

        # Set values for detailed mode
        shares_bought = quantity
        price_at_purchase = price_per_share
        amount = shares_bought * price_at_purchase

    else:
        # Quick mode: require amount, fetch price from yfinance
        if 'amount' not in data:
            return jsonify({'error': 'Missing required field: amount'}), 400

        try:
            amount = float(data['amount'])
        except (ValueError, TypeError):
            return jsonify({'error': 'amount must be a valid number'}), 400

        if amount <= 0:
            return jsonify({'error': 'amount must be positive'}), 400

        # Look up historical price on purchase date
        price_at_purchase = get_price_on_date(ticker, purchase_date)
        if price_at_purchase is None:
            return jsonify({'error': f'Unable to fetch price for {ticker} on {purchase_date}'}), 500

        # Calculate shares bought from amount and price
        shares_bought = amount / price_at_purchase

    purchase = Purchase(
        user_id=current_user.id,
        ticker=ticker,
        purchase_date=purchase_date,
        amount=amount,
        shares_bought=shares_bought,
        price_at_purchase=price_at_purchase
    )

    db.session.add(purchase)
    db.session.commit()

    # Invalidate price cache to ensure fresh prices on next fetch
    invalidate_price_cache()

    return jsonify(purchase.to_dict()), 201


@purchases_bp.route('/purchases/<int:id>', methods=['DELETE'])
@login_required
def delete_purchase(id):
    """Delete a purchase (must belong to current user)."""
    purchase = Purchase.query.filter_by(id=id, user_id=current_user.id).first()
    if not purchase:
        return jsonify({'error': 'Purchase not found'}), 404

    db.session.delete(purchase)
    db.session.commit()

    # Invalidate price cache to ensure fresh prices on next fetch
    invalidate_price_cache()

    return jsonify({'message': 'Purchase deleted'}), 200


@purchases_bp.route('/purchases/<int:id>/comparison', methods=['GET'])
@login_required
def get_purchase_comparison(id):
    """Get comparison data for a single purchase against benchmark stocks."""
    # Get the purchase (must belong to current user)
    purchase = Purchase.query.filter_by(id=id, user_id=current_user.id).first()
    if not purchase:
        return jsonify({'error': 'Purchase not found'}), 404

    # Get all default comparison stocks
    comparison_stocks = ComparisonStock.query.filter_by(is_default=True).all()

    # Calculate actual performance
    current_price = get_current_price(purchase.ticker)
    if current_price is None:
        return jsonify({'error': 'Unable to fetch current price for ticker'}), 500

    actual_current_value = purchase.shares_bought * current_price
    actual_gain_loss = actual_current_value - purchase.amount
    actual_return_pct = (actual_gain_loss / purchase.amount * 100) if purchase.amount > 0 else 0

    # Calculate alternatives
    alternatives = []
    for comp_stock in comparison_stocks:
        # Get price of comparison stock on purchase date
        if comp_stock.ticker == purchase.ticker:
            comp_price_at_purchase = purchase.price_at_purchase
        else:
            comp_price_at_purchase = get_price_on_date(comp_stock.ticker, purchase.purchase_date)
        if comp_price_at_purchase is None:
            continue

        # Calculate shares we would have bought
        shares_would_have = purchase.amount / comp_price_at_purchase

        # Get current price
        comp_current_price = get_current_price(comp_stock.ticker)
        if comp_current_price is None:
            continue

        # Calculate performance
        alt_current_value = shares_would_have * comp_current_price
        alt_gain_loss = alt_current_value - purchase.amount
        alt_return_pct = (alt_gain_loss / purchase.amount * 100) if purchase.amount > 0 else 0
        difference_vs_actual = alt_current_value - actual_current_value

        alternatives.append({
            'ticker': comp_stock.ticker,
            'name': comp_stock.name,
            'price_at_purchase': round(comp_price_at_purchase, 2),
            'shares_would_have': round(shares_would_have, 4),
            'current_price': round(comp_current_price, 2),
            'current_value': round(alt_current_value, 2),
            'gain_loss': round(alt_gain_loss, 2),
            'return_pct': round(alt_return_pct, 2),
            'difference_vs_actual': round(difference_vs_actual, 2)
        })

    # Get historical data for charting
    price_histories = {}
    all_tickers = [purchase.ticker] + [cs.ticker for cs in comparison_stocks]

    for ticker in all_tickers:
        price_histories[ticker] = get_price_history(ticker, purchase.purchase_date)

    # Build date series from actual ticker's history
    if price_histories.get(purchase.ticker):
        dates = sorted(price_histories[purchase.ticker].keys())
    else:
        dates = []

    # Calculate values for each date
    actual_history = []
    alt_histories = {cs.ticker: [] for cs in comparison_stocks}

    for date in dates:
        # Actual value on this date
        ticker_prices = price_histories.get(purchase.ticker, {})
        price = ticker_prices.get(date)
        if price:
            actual_value = purchase.shares_bought * price
            actual_history.append(round(actual_value, 2))
        else:
            actual_history.append(None)

        # Alternative values on this date
        for comp_stock in comparison_stocks:
            if comp_stock.ticker == purchase.ticker:
                comp_price_at_purchase = purchase.price_at_purchase
            else:
                comp_price_at_purchase = get_price_on_date(comp_stock.ticker, purchase.purchase_date)
            if comp_price_at_purchase:
                comp_shares = purchase.amount / comp_price_at_purchase
                comp_prices = price_histories.get(comp_stock.ticker, {})
                comp_price = comp_prices.get(date)
                if comp_price:
                    alt_value = comp_shares * comp_price
                    alt_histories[comp_stock.ticker].append(round(alt_value, 2))
                else:
                    alt_histories[comp_stock.ticker].append(None)
            else:
                alt_histories[comp_stock.ticker].append(None)

    return jsonify({
        'purchase': {
            'id': purchase.id,
            'ticker': purchase.ticker,
            'purchase_date': purchase.purchase_date.isoformat(),
            'amount': round(purchase.amount, 2),
            'shares_bought': round(purchase.shares_bought, 4),
            'price_at_purchase': round(purchase.price_at_purchase, 2)
        },
        'actual': {
            'current_price': round(current_price, 2),
            'current_value': round(actual_current_value, 2),
            'gain_loss': round(actual_gain_loss, 2),
            'return_pct': round(actual_return_pct, 2)
        },
        'alternatives': alternatives,
        'history': {
            'dates': [d.isoformat() for d in dates],
            'actual': actual_history,
            'alternatives': alt_histories
        }
    })
