from flask import Blueprint, jsonify, request, send_file
from flask_login import login_required, current_user
from app import db, csrf
from app.models import Purchase, ComparisonStock, PortfolioShare
from app.services.stock_data import get_price_on_date, get_current_prices
from app.services.image_generator import generate_share_image
import uuid
from io import BytesIO

share_bp = Blueprint('share', __name__)

# Note: POST /share/create and DELETE /share/<token> require CSRF protection
# because they modify data and require authentication.


@share_bp.route('/share/create', methods=['POST'])
@login_required
def create_share():
    """Create a shareable portfolio snapshot."""
    purchases = Purchase.query.filter_by(user_id=current_user.id).all()
    comparison_stocks = ComparisonStock.query.filter_by(is_default=True).all()

    if not purchases:
        return jsonify({'error': 'No purchases found to share'}), 400

    # Step 1: Collect all unique tickers (purchases + comparison stocks)
    purchase_tickers = list(set(p.ticker for p in purchases))
    comp_tickers = [cs.ticker for cs in comparison_stocks]
    all_tickers = list(set(purchase_tickers + comp_tickers))

    # Step 2: Batch fetch all current prices ONCE
    current_prices = get_current_prices(all_tickers)

    # Step 3: Pre-compute comparison stock prices at each unique purchase date
    unique_purchase_dates = list(set(p.purchase_date for p in purchases))
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
            'return_pct': alt_return_pct
        })

    # Find best and worst performing benchmarks
    if not alternatives:
        return jsonify({'error': 'No benchmark data available'}), 500

    best_benchmark = max(alternatives, key=lambda x: x['return_pct'])
    worst_benchmark = min(alternatives, key=lambda x: x['return_pct'])

    # Calculate opportunity cost (portfolio return - best benchmark return)
    opportunity_cost_pct = actual_return_pct - best_benchmark['return_pct']

    # Generate UUID4 token
    share_token = str(uuid.uuid4())

    # Store in PortfolioShare
    share = PortfolioShare(
        share_token=share_token,
        user_id=current_user.id,
        portfolio_return_pct=round(actual_return_pct, 2),
        best_benchmark_ticker=best_benchmark['ticker'],
        best_benchmark_name=best_benchmark['name'],
        best_benchmark_return_pct=round(best_benchmark['return_pct'], 2),
        worst_benchmark_ticker=worst_benchmark['ticker'],
        worst_benchmark_name=worst_benchmark['name'],
        worst_benchmark_return_pct=round(worst_benchmark['return_pct'], 2),
        opportunity_cost_pct=round(opportunity_cost_pct, 2)
    )

    db.session.add(share)
    db.session.commit()

    # Build share URL
    share_url = request.host_url.rstrip('/') + '/share/' + share_token

    return jsonify({
        'share_token': share_token,
        'share_url': share_url,
        'created_at': share.created_at.isoformat()
    }), 201


@share_bp.route('/share/<token>', methods=['GET'])
def get_share(token):
    """Get shareable portfolio snapshot (public, no auth required)."""
    share = PortfolioShare.query.filter_by(share_token=token).first()

    if not share:
        return jsonify({'error': 'Share not found'}), 404

    # Increment view count
    share.view_count += 1
    db.session.commit()

    return jsonify(share.to_dict())


@share_bp.route('/share/<token>/image', methods=['GET'])
def get_share_image(token):
    """Generate and return PNG image for shareable portfolio (public, no auth required)."""
    share = PortfolioShare.query.filter_by(share_token=token).first()

    if not share:
        return jsonify({'error': 'Share not found'}), 404

    # Generate PNG using image_generator (pass dict, not model)
    image_bytes = generate_share_image(share.to_dict())

    # Return image/png response
    return send_file(
        BytesIO(image_bytes),
        mimetype='image/png',
        as_attachment=False,
        download_name=f'honest-portfolio-{token[:8]}.png'
    )


@share_bp.route('/share/<token>', methods=['DELETE'])
@login_required
def delete_share(token):
    """Delete a shareable portfolio snapshot (requires auth, owner only)."""
    share = PortfolioShare.query.filter_by(share_token=token).first()

    if not share:
        return jsonify({'error': 'Share not found'}), 404

    # Verify current_user owns the share
    if share.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized to delete this share'}), 403

    db.session.delete(share)
    db.session.commit()

    return jsonify({'message': 'Share deleted successfully'}), 200
