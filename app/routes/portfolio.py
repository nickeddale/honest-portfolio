from flask import Blueprint, jsonify
from flask_login import login_required, current_user
from app.models import Purchase, ComparisonStock
from app.services.stock_data import get_price_on_date, get_current_prices, get_price_history

portfolio_bp = Blueprint('portfolio', __name__)


@portfolio_bp.route('/portfolio/summary', methods=['GET'])
@login_required
def get_portfolio_summary():
    """Get portfolio summary for the current user."""
    purchases = Purchase.query.filter_by(user_id=current_user.id).all()
    comparison_stocks = ComparisonStock.query.filter_by(is_default=True).all()

    if not purchases:
        return jsonify({
            'actual': {'total_invested': 0, 'current_value': 0, 'gain_loss': 0, 'return_pct': 0},
            'alternatives': []
        })

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


@portfolio_bp.route('/portfolio/history', methods=['GET'])
@login_required
def get_portfolio_history():
    """Get historical portfolio values for charting."""
    purchases = Purchase.query.filter_by(user_id=current_user.id).order_by(Purchase.purchase_date).all()
    comparison_stocks = ComparisonStock.query.filter_by(is_default=True).all()

    if not purchases:
        return jsonify({'dates': [], 'actual': [], 'alternatives': {}})

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
