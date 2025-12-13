from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app import db, csrf
from app.models import Purchase, ComparisonStock
from app.services.stock_data import (
    validate_ticker, is_trading_day, get_price_on_date,
    get_current_prices, get_price_history
)
from datetime import datetime
from collections import namedtuple

guest_bp = Blueprint('guest', __name__)

# Note: migrate_guest_purchases requires CSRF protection because it modifies
# the database (creates Purchase records). Other guest endpoints are stateless
# calculations that don't persist data.

# Simple namedtuple to represent guest purchases (no database interaction)
GuestPurchase = namedtuple('GuestPurchase', [
    'id', 'ticker', 'purchase_date', 'amount',
    'shares_bought', 'price_at_purchase'
])


@guest_bp.route('/guest/purchases/validate', methods=['POST'])
@csrf.exempt  # Stateless validation, no data persistence
def validate_purchase():
    """
    Validate a purchase and return calculated fields.
    Guest endpoint - no authentication required.
    """
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

    return jsonify({
        'ticker': ticker,
        'purchase_date': purchase_date.isoformat(),
        'amount': round(amount, 2),
        'shares_bought': round(shares_bought, 4),
        'price_at_purchase': round(price_at_purchase, 2)
    }), 200


@guest_bp.route('/guest/portfolio/summary', methods=['POST'])
@csrf.exempt  # Stateless calculation, no data persistence
def get_guest_portfolio_summary():
    """
    Get portfolio summary for guest purchases.
    Guest endpoint - no authentication required.
    Accepts purchases array in request body.
    """
    data = request.get_json()

    if 'purchases' not in data:
        return jsonify({'error': 'Missing required field: purchases'}), 400

    purchases_data = data['purchases']

    if not isinstance(purchases_data, list):
        return jsonify({'error': 'purchases must be an array'}), 400

    if not purchases_data:
        return jsonify({
            'actual': {'total_invested': 0, 'current_value': 0, 'gain_loss': 0, 'return_pct': 0},
            'alternatives': []
        })

    # Convert purchase dicts to GuestPurchase objects
    purchases = []
    for i, p in enumerate(purchases_data):
        try:
            # Parse purchase_date if it's a string
            if isinstance(p.get('purchase_date'), str):
                purchase_date = datetime.strptime(p['purchase_date'], '%Y-%m-%d').date()
            else:
                purchase_date = p['purchase_date']

            purchases.append(GuestPurchase(
                id=i,  # Use index as ID for guest purchases
                ticker=p['ticker'],
                purchase_date=purchase_date,
                amount=float(p['amount']),
                shares_bought=float(p['shares_bought']),
                price_at_purchase=float(p['price_at_purchase'])
            ))
        except (KeyError, ValueError, TypeError) as e:
            return jsonify({'error': f'Invalid purchase data at index {i}: {str(e)}'}), 400

    comparison_stocks = ComparisonStock.query.filter_by(is_default=True).all()

    # Step 1: Collect all unique tickers (purchases + comparison stocks)
    purchase_tickers = list(set(p.ticker for p in purchases))
    comp_tickers = [cs.ticker for cs in comparison_stocks]
    all_tickers = list(set(purchase_tickers + comp_tickers))

    # Step 2: Batch fetch all current prices ONCE
    current_prices = get_current_prices(all_tickers)

    # Step 3: Pre-compute comparison stock prices at each unique purchase date
    unique_purchase_dates = list(set(p.purchase_date for p in purchases))
    # Build a lookup dict: {(comp_ticker, date): price}
    comp_prices_at_dates = {}
    for comp_ticker in comp_tickers:
        for date in unique_purchase_dates:
            price = get_price_on_date(comp_ticker, date)
            comp_prices_at_dates[(comp_ticker, date)] = price

    # Calculate actual portfolio
    total_invested = sum(p.amount for p in purchases)
    actual_current_value = 0

    for purchase in purchases:
        current_price = current_prices.get(purchase.ticker)
        if current_price:
            actual_current_value += purchase.shares_bought * current_price

    actual_gain_loss = actual_current_value - total_invested
    actual_return_pct = (actual_gain_loss / total_invested * 100) if total_invested > 0 else 0

    # Calculate alternatives using pre-computed data
    alternatives = []
    for comp_stock in comparison_stocks:
        alt_current_value = 0
        comp_current_price = current_prices.get(comp_stock.ticker)

        for purchase in purchases:
            # Get price of comparison stock on original purchase date
            if comp_stock.ticker == purchase.ticker:
                comp_price_at_purchase = purchase.price_at_purchase
            else:
                comp_price_at_purchase = comp_prices_at_dates.get((comp_stock.ticker, purchase.purchase_date))

            if comp_price_at_purchase and comp_current_price:
                # Calculate how many shares we would have bought
                comp_shares = purchase.amount / comp_price_at_purchase
                # Use pre-fetched current price
                alt_current_value += comp_shares * comp_current_price

        alt_gain_loss = alt_current_value - total_invested
        alt_return_pct = (alt_gain_loss / total_invested * 100) if total_invested > 0 else 0

        alternatives.append({
            'ticker': comp_stock.ticker,
            'name': comp_stock.name,
            'total_invested': total_invested,
            'current_value': round(alt_current_value, 2),
            'gain_loss': round(alt_gain_loss, 2),
            'return_pct': round(alt_return_pct, 2)
        })

    return jsonify({
        'actual': {
            'total_invested': round(total_invested, 2),
            'current_value': round(actual_current_value, 2),
            'gain_loss': round(actual_gain_loss, 2),
            'return_pct': round(actual_return_pct, 2)
        },
        'alternatives': alternatives
    })


@guest_bp.route('/guest/portfolio/history', methods=['POST'])
@csrf.exempt  # Stateless calculation, no data persistence
def get_guest_portfolio_history():
    """
    Get historical portfolio values for charting.
    Guest endpoint - no authentication required.
    Accepts purchases array in request body.
    """
    data = request.get_json()

    if 'purchases' not in data:
        return jsonify({'error': 'Missing required field: purchases'}), 400

    purchases_data = data['purchases']

    if not isinstance(purchases_data, list):
        return jsonify({'error': 'purchases must be an array'}), 400

    if not purchases_data:
        return jsonify({'dates': [], 'actual': [], 'alternatives': {}})

    # Convert purchase dicts to GuestPurchase objects
    purchases = []
    for i, p in enumerate(purchases_data):
        try:
            # Parse purchase_date if it's a string
            if isinstance(p.get('purchase_date'), str):
                purchase_date = datetime.strptime(p['purchase_date'], '%Y-%m-%d').date()
            else:
                purchase_date = p['purchase_date']

            purchases.append(GuestPurchase(
                id=i,  # Use index as ID for guest purchases
                ticker=p['ticker'],
                purchase_date=purchase_date,
                amount=float(p['amount']),
                shares_bought=float(p['shares_bought']),
                price_at_purchase=float(p['price_at_purchase'])
            ))
        except (KeyError, ValueError, TypeError) as e:
            return jsonify({'error': f'Invalid purchase data at index {i}: {str(e)}'}), 400

    comparison_stocks = ComparisonStock.query.filter_by(is_default=True).all()

    # Get all unique tickers (actual + comparison)
    actual_tickers = list(set(p.ticker for p in purchases))
    comp_tickers = [cs.ticker for cs in comparison_stocks]
    all_tickers = actual_tickers + comp_tickers

    # Get start date (earliest purchase)
    start_date = min(p.purchase_date for p in purchases)

    # Get price history for all tickers
    price_histories = {}
    for ticker in all_tickers:
        price_histories[ticker] = get_price_history(ticker, start_date)

    # Build date series (use dates from any ticker's history)
    if price_histories.get(actual_tickers[0]):
        dates = list(price_histories[actual_tickers[0]].keys())
    else:
        return jsonify({'dates': [], 'actual': [], 'alternatives': {}})

    # Step 1: Pre-compute comparison stock prices at each unique purchase date
    unique_purchase_dates = list(set(p.purchase_date for p in purchases))
    # Build a lookup dict: {(comp_ticker, purchase_date): price}
    comp_prices_at_purchase = {}
    for comp_ticker in comp_tickers:
        for purchase_date in unique_purchase_dates:
            price = get_price_on_date(comp_ticker, purchase_date)
            comp_prices_at_purchase[(comp_ticker, purchase_date)] = price

    # Step 2: Pre-compute shares bought for each comparison stock per purchase
    # This eliminates repeated calculations in the date loop
    # Structure: {(comp_ticker, purchase_id): shares}
    comp_shares_per_purchase = {}
    for comp_stock in comparison_stocks:
        for purchase in purchases:
            if comp_stock.ticker == purchase.ticker:
                # Same ticker - use actual purchase price
                comp_price_at_purchase_date = purchase.price_at_purchase
            else:
                # Different ticker - use pre-computed price
                comp_price_at_purchase_date = comp_prices_at_purchase.get(
                    (comp_stock.ticker, purchase.purchase_date)
                )

            if comp_price_at_purchase_date:
                comp_shares = purchase.amount / comp_price_at_purchase_date
                comp_shares_per_purchase[(comp_stock.ticker, purchase.id)] = comp_shares

    # Calculate portfolio values for each date
    actual_values = []
    alt_values = {cs.ticker: [] for cs in comparison_stocks}

    for date in dates:
        # Actual portfolio value on this date
        actual_value = 0
        for purchase in purchases:
            if purchase.purchase_date <= date:
                ticker_prices = price_histories.get(purchase.ticker, {})
                price = ticker_prices.get(date)
                if price:
                    actual_value += purchase.shares_bought * price
        actual_values.append(round(actual_value, 2))

        # Alternative portfolio values using pre-computed shares
        for comp_stock in comparison_stocks:
            alt_value = 0
            for purchase in purchases:
                if purchase.purchase_date <= date:
                    # Use pre-computed shares
                    comp_shares = comp_shares_per_purchase.get((comp_stock.ticker, purchase.id))
                    if comp_shares:
                        # Value on this date using price history
                        comp_prices = price_histories.get(comp_stock.ticker, {})
                        comp_price = comp_prices.get(date)
                        if comp_price:
                            alt_value += comp_shares * comp_price
            alt_values[comp_stock.ticker].append(round(alt_value, 2))

    return jsonify({
        'dates': [d.isoformat() for d in dates],
        'actual': actual_values,
        'alternatives': alt_values
    })


@guest_bp.route('/guest/migrate', methods=['POST'])
@login_required
def migrate_guest_purchases():
    """
    Migrate guest purchases to authenticated user's account.
    Requires authentication.
    """
    data = request.get_json()

    if 'purchases' not in data:
        return jsonify({'error': 'Missing required field: purchases'}), 400

    purchases_data = data['purchases']

    if not isinstance(purchases_data, list):
        return jsonify({'error': 'purchases must be an array'}), 400

    migrated_count = 0
    errors = []

    for i, p in enumerate(purchases_data):
        try:
            # Parse purchase_date if it's a string
            if isinstance(p.get('purchase_date'), str):
                purchase_date = datetime.strptime(p['purchase_date'], '%Y-%m-%d').date()
            else:
                purchase_date = p['purchase_date']

            # Create Purchase record for current user
            purchase = Purchase(
                user_id=current_user.id,
                ticker=p['ticker'],
                purchase_date=purchase_date,
                amount=float(p['amount']),
                shares_bought=float(p['shares_bought']),
                price_at_purchase=float(p['price_at_purchase'])
            )

            db.session.add(purchase)
            migrated_count += 1

        except (KeyError, ValueError, TypeError) as e:
            errors.append(f'Purchase at index {i}: {str(e)}')

    # Commit all successful migrations
    if migrated_count > 0:
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': f'Database error: {str(e)}'}), 500

    return jsonify({
        'migrated': migrated_count,
        'errors': errors
    }), 200
