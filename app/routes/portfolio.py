from flask import Blueprint, jsonify
from flask_login import login_required, current_user
import math
from datetime import datetime
from app.models import Purchase, ComparisonStock
from app.services.stock_data import get_price_on_date, get_current_prices, get_price_history

portfolio_bp = Blueprint('portfolio', __name__)


def sanitize_float(value):
    """Convert NaN/Inf to None for valid JSON."""
    if value is None:
        return None
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    return value


def calculate_monthly_dca_spy(purchases, current_prices, price_histories=None):
    """
    Calculate Monthly DCA SPY alternative.

    Simulates: Equal monthly investments in SPY on last trading day of each month.
    """
    if not purchases:
        return None

    from app.services.stock_data import (
        generate_monthly_dca_dates,
        get_price_on_date
    )

    total_invested = sum(p.amount for p in purchases)
    start_date = min(p.purchase_date for p in purchases)
    end_date = datetime.now().date()

    monthly_dates = generate_monthly_dca_dates(start_date, end_date)

    if not monthly_dates:
        return None

    monthly_investment = total_invested / len(monthly_dates)
    spy_current_price = current_prices.get('SPY')

    if not spy_current_price:
        return None

    # Accumulate shares from monthly purchases
    total_shares = 0
    for year, month, trading_date in monthly_dates:
        if price_histories and 'SPY' in price_histories:
            spy_price = price_histories['SPY'].get(trading_date)
        else:
            spy_price = get_price_on_date('SPY', trading_date)

        if spy_price:
            total_shares += monthly_investment / spy_price

    current_value = total_shares * spy_current_price
    gain_loss = current_value - total_invested
    return_pct = (gain_loss / total_invested * 100) if total_invested > 0 else 0

    return {
        'ticker': 'MONTHLY_DCA_SPY',
        'name': 'Monthly DCA SPY',
        'total_invested': sanitize_float(total_invested),
        'current_value': sanitize_float(round(current_value, 2)),
        'gain_loss': sanitize_float(round(gain_loss, 2)),
        'return_pct': sanitize_float(round(return_pct, 2))
    }


def calculate_monthly_dca_spy_history(purchases, price_histories, dates):
    """
    Calculate Monthly DCA SPY time series for history chart.

    For each date: calculates cumulative value based on monthly DCA purchases made up to that point.
    """
    from app.services.stock_data import generate_monthly_dca_dates

    if not purchases or 'SPY' not in price_histories:
        return [None] * len(dates)

    total_invested = sum(p.amount for p in purchases)
    start_date = min(p.purchase_date for p in purchases)

    all_monthly_dates = generate_monthly_dca_dates(start_date)
    num_months = len(all_monthly_dates)

    if num_months == 0:
        return [None] * len(dates)

    monthly_investment = total_invested / num_months

    # Pre-compute shares bought on each monthly date
    shares_by_date = {}
    for year, month, trading_date in all_monthly_dates:
        spy_price = price_histories['SPY'].get(trading_date)
        if spy_price:
            shares_by_date[trading_date] = monthly_investment / spy_price

    # Calculate value for each date in series
    values = []
    for date in dates:
        total_shares = sum(
            shares for purchase_date, shares in shares_by_date.items()
            if purchase_date <= date
        )

        spy_price = price_histories['SPY'].get(date)

        if spy_price and total_shares > 0:
            values.append(sanitize_float(round(total_shares * spy_price, 2)))
        else:
            values.append(None)

    return values


@portfolio_bp.route('/portfolio/summary', methods=['GET'])
@login_required
def get_portfolio_summary():
    """Get portfolio summary for the current user."""
    from app.models import Sale, PurchaseSaleAssignment

    purchases = Purchase.query.filter_by(user_id=current_user.id).all()
    sales = Sale.query.filter_by(user_id=current_user.id).all()
    comparison_stocks = ComparisonStock.query.filter_by(is_default=True).all()

    if not purchases:
        return jsonify({
            'actual': {
                'total_invested': 0,
                'current_value': 0,
                'unrealized_gains': 0,
                'realized_gains': 0,
                'cash_position': 0,
                'gain_loss': 0,
                'return_pct': 0
            },
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

    # Calculate actual portfolio metrics
    total_invested = sum(p.amount for p in purchases)

    # Calculate realized gains from sales
    realized_gains = 0
    for sale in sales:
        for assignment in sale.purchase_assignments:
            realized_gains += assignment.realized_gain_loss

    # Calculate cash position from sales
    cash_position = sum(sale.cash_retained or 0 for sale in sales)

    # Calculate current holdings value using shares_remaining
    current_holdings_value = 0
    cost_basis_remaining = 0

    for purchase in purchases:
        current_price = current_prices.get(purchase.ticker)
        if current_price:
            current_holdings_value += purchase.shares_remaining * current_price
        cost_basis_remaining += purchase.shares_remaining * purchase.price_at_purchase

    # Calculate unrealized gains from remaining holdings
    unrealized_gains = current_holdings_value - cost_basis_remaining

    # Total current value includes holdings + cash
    actual_current_value = current_holdings_value + cash_position

    # Total gain/loss includes both realized and unrealized
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
            'total_invested': sanitize_float(total_invested),
            'current_value': sanitize_float(round(alt_current_value, 2)),
            'gain_loss': sanitize_float(round(alt_gain_loss, 2)),
            'return_pct': sanitize_float(round(alt_return_pct, 2))
        })

    # Calculate Monthly DCA SPY alternative
    monthly_dca = calculate_monthly_dca_spy(purchases, current_prices)
    if monthly_dca:
        alternatives.append(monthly_dca)

    return jsonify({
        'actual': {
            'total_invested': sanitize_float(round(total_invested, 2)),
            'current_value': sanitize_float(round(actual_current_value, 2)),
            'unrealized_gains': sanitize_float(round(unrealized_gains, 2)),
            'realized_gains': sanitize_float(round(realized_gains, 2)),
            'cash_position': sanitize_float(round(cash_position, 2)),
            'gain_loss': sanitize_float(round(actual_gain_loss, 2)),
            'return_pct': sanitize_float(round(actual_return_pct, 2))
        },
        'alternatives': alternatives
    })


@portfolio_bp.route('/portfolio/history', methods=['GET'])
@login_required
def get_portfolio_history():
    """Get historical portfolio values for charting."""
    from app.models import Sale, PurchaseSaleAssignment

    purchases = Purchase.query.filter_by(user_id=current_user.id).order_by(Purchase.purchase_date).all()
    sales = Sale.query.filter_by(user_id=current_user.id).order_by(Sale.sale_date).all()
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

    # Step 3: Pre-compute shares sold on or before each date for each purchase
    # Structure: {(purchase_id, date): shares_sold_by_date}
    shares_sold_by_date = {}
    for purchase in purchases:
        for date in dates:
            shares_sold = 0
            for assignment in purchase.sale_assignments:
                if assignment.sale.sale_date <= date:
                    shares_sold += assignment.shares_assigned
            shares_sold_by_date[(purchase.id, date)] = shares_sold

    # Calculate portfolio values for each date
    actual_values = []
    alt_values = {cs.ticker: [] for cs in comparison_stocks}

    for date in dates:
        # Actual portfolio value on this date (using shares_remaining on that date)
        actual_value = 0
        for purchase in purchases:
            if purchase.purchase_date <= date:
                # Calculate shares remaining on this specific date
                shares_sold = shares_sold_by_date.get((purchase.id, date), 0)
                shares_remaining_on_date = purchase.shares_bought - shares_sold

                ticker_prices = price_histories.get(purchase.ticker, {})
                price = ticker_prices.get(date)
                if price and shares_remaining_on_date > 0:
                    actual_value += shares_remaining_on_date * price
        actual_values.append(sanitize_float(round(actual_value, 2)))

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
            alt_values[comp_stock.ticker].append(sanitize_float(round(alt_value, 2)))

    # Calculate Monthly DCA SPY history
    monthly_dca_values = calculate_monthly_dca_spy_history(
        purchases,
        price_histories,
        dates
    )
    alt_values['MONTHLY_DCA_SPY'] = monthly_dca_values

    return jsonify({
        'dates': [d.isoformat() for d in dates],
        'actual': actual_values,
        'alternatives': alt_values
    })
