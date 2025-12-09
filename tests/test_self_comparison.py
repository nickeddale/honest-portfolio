"""
End-to-end test for the self-comparison price fix.

This test verifies that when a purchase is compared against itself
(e.g., META purchase compared to META benchmark), the comparison uses
the stored purchase price rather than a potentially different cached price.

Bug context: yfinance adjusted close prices can change over time, causing
self-comparisons to show incorrect differences. The fix ensures
self-comparisons always use the original purchase price.
"""
import pytest
from datetime import date
from app.models import Purchase, ComparisonStock, PriceCache
from app import db


class TestSelfComparisonPriceFix:
    """Test suite for verifying the self-comparison price fix."""

    def test_self_comparison_uses_stored_purchase_price(
        self, mock_stock_prices, client, app, db_session, seed_comparison_stocks
    ):
        """
        Test that self-comparison (META vs META) uses the stored purchase price.

        This is the core E2E test that verifies the bug fix:
        1. Create a META purchase with a known price
        2. Simulate a different cached price for META on the same date
        3. Call the comparison endpoint
        4. Verify that the META comparison uses the purchase price, not cached price
        5. Verify that difference_vs_actual is 0.0 for self-comparison
        """
        # Step 1: Create a META purchase with a specific known price
        purchase_date = date(2024, 1, 15)
        purchase_price = 500.00
        purchase_amount = 10000.00
        shares_bought = purchase_amount / purchase_price  # 20.0 shares

        purchase = Purchase(
            ticker='META',
            purchase_date=purchase_date,
            amount=purchase_amount,
            shares_bought=shares_bought,
            price_at_purchase=purchase_price
        )
        db_session.add(purchase)
        db_session.commit()

        purchase_id = purchase.id

        # Step 2: Add a DIFFERENT cached price for META on the same date
        # This simulates the scenario where yfinance returns a different
        # adjusted close price when fetched at a later time
        different_cached_price = 485.00  # Different from purchase_price!

        cached_price = PriceCache(
            ticker='META',
            date=purchase_date,
            close_price=different_cached_price
        )
        db_session.add(cached_price)
        db_session.commit()

        # Step 3: Call the comparison endpoint
        with app.app_context():
            response = client.get(f'/api/purchases/{purchase_id}/comparison')

        # Verify response is successful
        assert response.status_code == 200
        data = response.get_json()

        # Verify response structure
        assert 'purchase' in data
        assert 'actual' in data
        assert 'alternatives' in data

        # Step 4: Find the META alternative in the comparison
        meta_comparison = None
        for alternative in data['alternatives']:
            if alternative['ticker'] == 'META':
                meta_comparison = alternative
                break

        # Ensure META is in the alternatives list
        assert meta_comparison is not None, "META should be in the comparison alternatives"

        # Step 5: CRITICAL ASSERTIONS - Verify the fix
        # The META comparison should use the stored purchase price (500.00),
        # NOT the cached price (485.00)
        assert meta_comparison['price_at_purchase'] == purchase_price, (
            f"Self-comparison should use stored purchase price {purchase_price}, "
            f"not cached price {different_cached_price}. "
            f"Got: {meta_comparison['price_at_purchase']}"
        )

        # Verify that self-comparison shows zero difference
        assert meta_comparison['difference_vs_actual'] == 0.0, (
            "Self-comparison should show zero difference vs actual. "
            f"Got: {meta_comparison['difference_vs_actual']}"
        )

        # Additional verification: shares calculation should match
        expected_shares = purchase_amount / purchase_price  # 20.0
        assert meta_comparison['shares_would_have'] == round(expected_shares, 4), (
            f"Self-comparison shares should match actual shares. "
            f"Expected: {round(expected_shares, 4)}, Got: {meta_comparison['shares_would_have']}"
        )

    def test_different_ticker_comparison_uses_cached_price(
        self, mock_stock_prices, client, app, db_session, seed_comparison_stocks
    ):
        """
        Test that comparisons to DIFFERENT tickers still use cached prices.

        This verifies that the fix only affects self-comparisons and doesn't
        break normal cross-ticker comparisons.
        """
        # Create a META purchase
        purchase_date = date(2024, 1, 15)
        purchase_price = 500.00
        purchase_amount = 10000.00

        purchase = Purchase(
            ticker='META',
            purchase_date=purchase_date,
            amount=purchase_amount,
            shares_bought=purchase_amount / purchase_price,
            price_at_purchase=purchase_price
        )
        db_session.add(purchase)
        db_session.commit()

        purchase_id = purchase.id

        # Add cached prices for other stocks
        # AAPL cached price
        aapl_cached_price = 180.00
        cached_aapl = PriceCache(
            ticker='AAPL',
            date=purchase_date,
            close_price=aapl_cached_price
        )
        db_session.add(cached_aapl)
        db_session.commit()

        # Call the comparison endpoint
        with app.app_context():
            response = client.get(f'/api/purchases/{purchase_id}/comparison')

        assert response.status_code == 200
        data = response.get_json()

        # Find AAPL in alternatives
        aapl_comparison = None
        for alternative in data['alternatives']:
            if alternative['ticker'] == 'AAPL':
                aapl_comparison = alternative
                break

        # AAPL comparison should use the cached/mocked price, NOT the purchase price
        assert aapl_comparison is not None
        # The mock returns 180.00 for AAPL
        assert aapl_comparison['price_at_purchase'] == 180.00

    def test_self_comparison_with_no_cached_price(
        self, mock_stock_prices, client, app, db_session, seed_comparison_stocks
    ):
        """
        Test self-comparison when there's no cached price.

        Verifies that even without a cache entry, self-comparison
        uses the stored purchase price.
        """
        # Create a META purchase
        purchase_date = date(2024, 1, 15)
        purchase_price = 500.00
        purchase_amount = 10000.00

        purchase = Purchase(
            ticker='META',
            purchase_date=purchase_date,
            amount=purchase_amount,
            shares_bought=purchase_amount / purchase_price,
            price_at_purchase=purchase_price
        )
        db_session.add(purchase)
        db_session.commit()

        purchase_id = purchase.id

        # Explicitly ensure NO cached price for META
        # (don't add any PriceCache entry)

        # Call the comparison endpoint
        with app.app_context():
            response = client.get(f'/api/purchases/{purchase_id}/comparison')

        assert response.status_code == 200
        data = response.get_json()

        # Find META in alternatives
        meta_comparison = None
        for alternative in data['alternatives']:
            if alternative['ticker'] == 'META':
                meta_comparison = alternative
                break

        assert meta_comparison is not None

        # Should still use the stored purchase price
        assert meta_comparison['price_at_purchase'] == purchase_price
        assert meta_comparison['difference_vs_actual'] == 0.0

    def test_purchase_summary_data(
        self, mock_stock_prices, client, app, db_session, seed_comparison_stocks
    ):
        """
        Test that the purchase summary data is correctly returned.

        This is a sanity check to ensure the overall endpoint structure is correct.
        """
        purchase_date = date(2024, 1, 15)
        purchase_price = 500.00
        purchase_amount = 10000.00
        shares_bought = 20.0

        purchase = Purchase(
            ticker='META',
            purchase_date=purchase_date,
            amount=purchase_amount,
            shares_bought=shares_bought,
            price_at_purchase=purchase_price
        )
        db_session.add(purchase)
        db_session.commit()

        purchase_id = purchase.id

        with app.app_context():
            response = client.get(f'/api/purchases/{purchase_id}/comparison')

        assert response.status_code == 200
        data = response.get_json()

        # Verify purchase summary
        assert data['purchase']['ticker'] == 'META'
        assert data['purchase']['amount'] == round(purchase_amount, 2)
        assert data['purchase']['shares_bought'] == round(shares_bought, 4)
        assert data['purchase']['price_at_purchase'] == round(purchase_price, 2)

        # Verify actual performance data exists
        assert 'current_price' in data['actual']
        assert 'current_value' in data['actual']
        assert 'gain_loss' in data['actual']
        assert 'return_pct' in data['actual']

        # Mock returns 550.00 as current price for META (10% gain)
        # Current value = 20 shares * 550 = 11000
        # Gain = 11000 - 10000 = 1000
        # Return = 1000 / 10000 * 100 = 10%
        assert data['actual']['current_price'] == 550.00
        assert data['actual']['current_value'] == 11000.00
        assert data['actual']['gain_loss'] == 1000.00
        assert data['actual']['return_pct'] == 10.00

    def test_all_comparison_stocks_present(
        self, mock_stock_prices, client, app, db_session, seed_comparison_stocks
    ):
        """
        Test that all default comparison stocks are included in the response.
        """
        purchase = Purchase(
            ticker='META',
            purchase_date=date(2024, 1, 15),
            amount=10000.00,
            shares_bought=20.0,
            price_at_purchase=500.00
        )
        db_session.add(purchase)
        db_session.commit()

        purchase_id = purchase.id

        with app.app_context():
            response = client.get(f'/api/purchases/{purchase_id}/comparison')

        assert response.status_code == 200
        data = response.get_json()

        # Verify all default comparison stocks are present
        alternative_tickers = {alt['ticker'] for alt in data['alternatives']}
        expected_tickers = {'SPY', 'AAPL', 'META', 'GOOGL', 'NVDA', 'AMZN'}

        assert alternative_tickers == expected_tickers, (
            f"Missing comparison stocks. Expected: {expected_tickers}, "
            f"Got: {alternative_tickers}"
        )
