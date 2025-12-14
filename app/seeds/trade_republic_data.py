"""Seed script for Trade Republic trade data.

Trade data extracted from Trade Republic account statement (Jan-Dec 2025).
Original amounts are in EUR. USD amounts are calculated using approximate
EUR/USD exchange rate of 1.08 for the period.
"""
from datetime import datetime
from app import db
from app.models import Purchase

# Approximate EUR/USD rate for 2025
EUR_USD_RATE = 1.08

# Trade Republic data: EUR trades mapped to US tickers
# (date, ticker, shares, eur_amount)
TRADE_DATA = [
    ('2025-01-07', 'SPY', 1.483434, 900.97),
    ('2025-01-27', 'NVDA', 13.445679, 1501.81),
    ('2025-02-25', 'SPY', 1.487357, 901.00),
    ('2025-03-05', 'NVDA', 14.050206, 1501.00),
    ('2025-03-05', 'MELI', 1.13907, 2201.00),
    ('2025-03-07', 'SPY', 1.594896, 901.00),
    ('2025-03-07', 'META', 1.724137, 1000.83),
    ('2025-03-07', 'AMZN', 5.405989, 1001.00),
    ('2025-04-03', 'SPY', 1.711482, 901.00),
    ('2025-04-04', 'NVDA', 11.284134, 1000.10),
    ('2025-04-04', 'META', 1.097815, 501.05),
    ('2025-04-04', 'AMZN', 3.305129, 501.07),
    ('2025-04-22', 'NVDA', 11.839924, 1001.00),
    ('2025-11-04', 'META', 9.110787, 5001.91),
]


def seed_trade_republic_data():
    """Load Trade Republic test data into the database.

    Uses stored EUR amounts and converts to USD using a fixed exchange rate.
    The original EUR values are preserved in original_amount/original_currency.
    """
    print("Starting Trade Republic data seed...")

    seeded_count = 0
    skipped_count = 0

    for date_str, ticker, shares, eur_amount in TRADE_DATA:
        # Parse the date
        purchase_date = datetime.strptime(date_str, '%Y-%m-%d').date()

        # Check if this purchase already exists (idempotent)
        existing = Purchase.query.filter_by(
            ticker=ticker,
            purchase_date=purchase_date,
            shares_bought=shares
        ).first()

        if existing:
            print(f"Skipping existing purchase: {ticker} on {date_str}")
            skipped_count += 1
            continue

        # Convert EUR to USD using fixed rate
        usd_amount = eur_amount * EUR_USD_RATE

        # Calculate price per share in USD
        usd_price = usd_amount / shares

        # Create the purchase record
        purchase = Purchase(
            ticker=ticker,
            purchase_date=purchase_date,
            amount=usd_amount,
            shares_bought=shares,
            price_at_purchase=usd_price,
            original_amount=eur_amount,
            original_currency='EUR'
        )

        db.session.add(purchase)
        print(f"Added: {ticker} - {shares:.6f} shares @ ${usd_price:.2f} (EUR {eur_amount:.2f})")
        seeded_count += 1

    # Commit all purchases
    try:
        db.session.commit()
        print(f"\nSeed complete! Added {seeded_count} purchases, skipped {skipped_count}.")
    except Exception as e:
        db.session.rollback()
        print(f"Error committing to database: {e}")
        raise


if __name__ == '__main__':
    from app import create_app

    app = create_app()
    with app.app_context():
        seed_trade_republic_data()
