"""
Example usage of the stock sales feature (Phase 1).

This demonstrates how to use the sale_service module to:
1. Preview FIFO assignment before creating a sale
2. Create a sale with automatic FIFO cost basis assignment
3. Link a sale to a reinvestment purchase

NOTE: This is for reference only. To actually use in the application,
you would call these functions from API endpoints or CLI commands.
"""

from datetime import date
from app import create_app, db
from app.models import User, Purchase, Sale
from app.services.sale_service import (
    create_sale_with_fifo,
    link_sale_to_reinvestment,
    preview_fifo_assignment,
    InsufficientSharesError
)


def example_scenario():
    """
    Example scenario: User sells some AAPL shares using FIFO cost basis.
    """
    app = create_app()

    with app.app_context():
        # Get or create a test user
        user = User.query.filter_by(email='test@example.com').first()
        if not user:
            user = User(
                email='test@example.com',
                name='Test User'
            )
            db.session.add(user)
            db.session.commit()

        print(f"\n{'='*60}")
        print(f"Stock Sales Example - User: {user.name}")
        print(f"{'='*60}\n")

        # Create some test purchases if they don't exist
        existing_purchases = Purchase.query.filter_by(
            user_id=user.id,
            ticker='AAPL'
        ).count()

        if existing_purchases == 0:
            print("Creating test purchases...")

            purchase1 = Purchase(
                user_id=user.id,
                ticker='AAPL',
                purchase_date=date(2024, 1, 15),
                shares_bought=100.0,
                price_at_purchase=150.0,
                amount=15000.0
            )

            purchase2 = Purchase(
                user_id=user.id,
                ticker='AAPL',
                purchase_date=date(2024, 3, 20),
                shares_bought=50.0,
                price_at_purchase=160.0,
                amount=8000.0
            )

            purchase3 = Purchase(
                user_id=user.id,
                ticker='AAPL',
                purchase_date=date(2024, 5, 10),
                shares_bought=75.0,
                price_at_purchase=155.0,
                amount=11625.0
            )

            db.session.add_all([purchase1, purchase2, purchase3])
            db.session.commit()

            print(f"  ✓ Created Purchase 1: {purchase1.shares_bought} shares @ ${purchase1.price_at_purchase}")
            print(f"  ✓ Created Purchase 2: {purchase2.shares_bought} shares @ ${purchase2.price_at_purchase}")
            print(f"  ✓ Created Purchase 3: {purchase3.shares_bought} shares @ ${purchase3.price_at_purchase}")
            print()

        # Show current holdings
        purchases = Purchase.query.filter_by(
            user_id=user.id,
            ticker='AAPL'
        ).order_by(Purchase.purchase_date).all()

        print("Current AAPL Holdings:")
        print(f"{'Date':<12} {'Shares Bought':<15} {'Price':<10} {'Shares Remaining':<18} {'Cost Basis':<12}")
        print("-" * 80)

        total_shares = 0
        total_cost = 0

        for p in purchases:
            cost = p.shares_remaining * p.price_at_purchase
            total_shares += p.shares_remaining
            total_cost += cost

            print(f"{p.purchase_date.isoformat():<12} "
                  f"{p.shares_bought:<15.2f} "
                  f"${p.price_at_purchase:<9.2f} "
                  f"{p.shares_remaining:<18.2f} "
                  f"${cost:>11.2f}")

        print("-" * 80)
        print(f"{'TOTAL':<42} {total_shares:<18.2f} ${total_cost:>11.2f}\n")

        # Step 1: Preview FIFO assignment
        print("\nStep 1: Preview FIFO Assignment")
        print("-" * 60)

        shares_to_sell = 120.0
        sale_price = 170.0

        print(f"Planning to sell {shares_to_sell} shares @ ${sale_price}")
        print()

        preview = preview_fifo_assignment(
            user_id=user.id,
            ticker='AAPL',
            shares_to_sell=shares_to_sell
        )

        if not preview['is_sufficient']:
            print(f"❌ ERROR: {preview.get('error', 'Insufficient shares')}")
            return

        print("FIFO Assignment Preview:")
        print(f"{'Purchase Date':<15} {'Available':<12} {'To Assign':<12} {'Cost Basis':<12}")
        print("-" * 60)

        for assignment in preview['assignments']:
            print(f"{assignment['purchase_date']:<15} "
                  f"{assignment['shares_available']:<12.2f} "
                  f"{assignment['shares_to_assign']:<12.2f} "
                  f"${assignment['cost_basis']:>10.2f}")

        print("-" * 60)
        print(f"Total Cost Basis: ${preview['total_cost_basis']:.2f}")
        print(f"Total Proceeds: ${shares_to_sell * sale_price:.2f}")
        print(f"Estimated Gain: ${(shares_to_sell * sale_price) - preview['total_cost_basis']:.2f}")
        print(f"Shares Remaining After Sale: {preview['shares_remaining_after']:.2f}\n")

        # Step 2: Execute the sale
        print("\nStep 2: Execute Sale with FIFO")
        print("-" * 60)

        try:
            sale = create_sale_with_fifo(
                user_id=user.id,
                ticker='AAPL',
                sale_date=date(2024, 6, 1),
                shares_sold=shares_to_sell,
                price_at_sale=sale_price
            )

            print(f"✓ Sale created successfully!")
            print(f"  Sale ID: {sale.id}")
            print(f"  Shares Sold: {sale.shares_sold}")
            print(f"  Price: ${sale.price_at_sale}")
            print(f"  Total Proceeds: ${sale.total_proceeds:.2f}")
            print()

            # Show assignments
            print("FIFO Assignments Created:")
            print(f"{'Purchase ID':<12} {'Shares':<12} {'Cost Basis':<12} {'Proceeds':<12} {'Gain/Loss':<12}")
            print("-" * 70)

            total_gain = 0
            for assignment in sale.purchase_assignments:
                total_gain += assignment.realized_gain_loss
                print(f"{assignment.purchase_id:<12} "
                      f"{assignment.shares_assigned:<12.2f} "
                      f"${assignment.cost_basis:<11.2f} "
                      f"${assignment.proceeds:<11.2f} "
                      f"${assignment.realized_gain_loss:>10.2f}")

            print("-" * 70)
            print(f"{'TOTAL':<36} ${sale.total_proceeds:.2f}  ${total_gain:>10.2f}\n")

            # Step 3: (Optional) Link to reinvestment
            print("\nStep 3: (Optional) Link Sale to Reinvestment")
            print("-" * 60)

            # Create a new purchase as reinvestment
            reinvestment_amount = 15000.0

            new_purchase = Purchase(
                user_id=user.id,
                ticker='MSFT',
                purchase_date=date(2024, 6, 5),
                shares_bought=reinvestment_amount / 350.0,  # ~42.86 shares @ $350
                price_at_purchase=350.0,
                amount=reinvestment_amount
            )
            db.session.add(new_purchase)
            db.session.commit()

            print(f"Created reinvestment purchase:")
            print(f"  Ticker: {new_purchase.ticker}")
            print(f"  Shares: {new_purchase.shares_bought:.2f}")
            print(f"  Amount: ${new_purchase.amount:.2f}")
            print()

            # Link the sale to the reinvestment
            updated_sale = link_sale_to_reinvestment(
                sale_id=sale.id,
                purchase_id=new_purchase.id,
                reinvested_amount=reinvestment_amount
            )

            print(f"✓ Sale linked to reinvestment!")
            print(f"  Sale Proceeds: ${updated_sale.total_proceeds:.2f}")
            print(f"  Reinvested Amount: ${updated_sale.reinvested_amount:.2f}")
            print(f"  Cash Retained: ${updated_sale.cash_retained:.2f}\n")

            # Show final holdings
            print("\nFinal AAPL Holdings After Sale:")
            print(f"{'Date':<12} {'Shares Bought':<15} {'Shares Remaining':<18}")
            print("-" * 50)

            for p in purchases:
                # Refresh to get updated shares_remaining
                db.session.refresh(p)
                print(f"{p.purchase_date.isoformat():<12} "
                      f"{p.shares_bought:<15.2f} "
                      f"{p.shares_remaining:<18.2f}")

            print()

        except InsufficientSharesError as e:
            print(f"❌ ERROR: {e}")

        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            db.session.rollback()


def example_insufficient_shares():
    """
    Example: Attempting to sell more shares than available.
    """
    app = create_app()

    with app.app_context():
        user = User.query.filter_by(email='test@example.com').first()
        if not user:
            print("Run example_scenario() first to create test data")
            return

        print(f"\n{'='*60}")
        print("Example: Insufficient Shares Error")
        print(f"{'='*60}\n")

        try:
            # Try to sell more shares than available
            create_sale_with_fifo(
                user_id=user.id,
                ticker='AAPL',
                sale_date=date(2024, 6, 1),
                shares_sold=1000.0,  # Way more than owned
                price_at_sale=170.0
            )
        except InsufficientSharesError as e:
            print(f"✓ Expected error caught: {e}\n")


if __name__ == '__main__':
    print("\n" + "="*60)
    print("Stock Sales Feature - Usage Examples")
    print("="*60)

    example_scenario()
    example_insufficient_shares()

    print("\n" + "="*60)
    print("Examples completed successfully!")
    print("="*60 + "\n")
