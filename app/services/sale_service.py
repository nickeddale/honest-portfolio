"""Service for handling stock sales with FIFO cost basis assignment."""

from datetime import datetime
from app import db
from app.models import Purchase, Sale, PurchaseSaleAssignment


class InsufficientSharesError(ValueError):
    """Raised when attempting to sell more shares than available."""
    pass


def create_sale_with_fifo(user_id, ticker, sale_date, shares_sold, price_at_sale):
    """
    Create a sale record and assign shares using FIFO (First In, First Out) method.

    Args:
        user_id (int): User ID who owns the purchases
        ticker (str): Stock ticker symbol
        sale_date (date or datetime): Date of sale
        shares_sold (float): Number of shares being sold
        price_at_sale (float): Price per share at time of sale

    Returns:
        Sale: The created sale record with FIFO assignments

    Raises:
        InsufficientSharesError: If not enough shares available to sell
        ValueError: If invalid parameters provided
    """
    # Input validation
    if shares_sold <= 0:
        raise ValueError("shares_sold must be positive")
    if price_at_sale <= 0:
        raise ValueError("price_at_sale must be positive")

    # Convert datetime to date if needed
    if isinstance(sale_date, datetime):
        sale_date = sale_date.date()

    # Get all purchases for this ticker ordered by purchase_date (FIFO)
    purchases = (Purchase.query
                .filter_by(user_id=user_id, ticker=ticker)
                .order_by(Purchase.purchase_date.asc())
                .all())

    if not purchases:
        raise InsufficientSharesError(f"No purchases found for ticker {ticker}")

    # Calculate total shares available
    total_available = sum(p.shares_remaining for p in purchases)

    # Use tolerance for floating point comparison
    TOLERANCE = 0.0001
    if total_available < shares_sold - TOLERANCE:
        raise InsufficientSharesError(
            f"Insufficient shares available. Available: {total_available:.4f}, "
            f"Requested: {shares_sold:.4f}"
        )

    # Create the sale record
    total_proceeds = shares_sold * price_at_sale
    sale = Sale(
        user_id=user_id,
        ticker=ticker,
        sale_date=sale_date,
        shares_sold=shares_sold,
        price_at_sale=price_at_sale,
        total_proceeds=total_proceeds
    )
    db.session.add(sale)
    db.session.flush()  # Get sale.id without committing

    # FIFO assignment loop
    remaining_to_sell = shares_sold

    for purchase in purchases:
        if remaining_to_sell <= TOLERANCE:
            break

        available_from_purchase = purchase.shares_remaining

        if available_from_purchase <= TOLERANCE:
            continue

        # Determine how many shares to assign from this purchase
        shares_to_assign = min(remaining_to_sell, available_from_purchase)

        # Calculate cost basis and proceeds for this assignment
        cost_basis = shares_to_assign * purchase.price_at_purchase
        proceeds = shares_to_assign * price_at_sale
        realized_gain_loss = proceeds - cost_basis

        # Create assignment record
        assignment = PurchaseSaleAssignment(
            purchase_id=purchase.id,
            sale_id=sale.id,
            shares_assigned=shares_to_assign,
            cost_basis=cost_basis,
            proceeds=proceeds,
            realized_gain_loss=realized_gain_loss
        )
        db.session.add(assignment)

        remaining_to_sell -= shares_to_assign

    # Final validation - ensure we assigned all shares (within tolerance)
    if remaining_to_sell > TOLERANCE:
        db.session.rollback()
        raise InsufficientSharesError(
            f"Failed to assign all shares. Remaining: {remaining_to_sell:.4f}"
        )

    # Commit the transaction
    db.session.commit()

    return sale


def link_sale_to_reinvestment(sale_id, purchase_id, reinvested_amount):
    """
    Link a sale to a reinvestment purchase.

    Args:
        sale_id (int): ID of the sale
        purchase_id (int): ID of the reinvestment purchase
        reinvested_amount (float): Amount reinvested from sale proceeds

    Returns:
        Sale: Updated sale record

    Raises:
        ValueError: If sale or purchase not found, or invalid amounts
    """
    sale = Sale.query.get(sale_id)
    if not sale:
        raise ValueError(f"Sale {sale_id} not found")

    purchase = Purchase.query.get(purchase_id)
    if not purchase:
        raise ValueError(f"Purchase {purchase_id} not found")

    if reinvested_amount <= 0:
        raise ValueError("reinvested_amount must be positive")

    if reinvested_amount > sale.total_proceeds:
        raise ValueError(
            f"reinvested_amount ({reinvested_amount}) cannot exceed "
            f"total_proceeds ({sale.total_proceeds})"
        )

    # Update sale with reinvestment info
    sale.reinvestment_purchase_id = purchase_id
    sale.reinvested_amount = reinvested_amount
    sale.cash_retained = sale.total_proceeds - reinvested_amount

    db.session.commit()

    return sale


def preview_fifo_assignment(user_id, ticker, shares_to_sell):
    """
    Preview how shares would be assigned using FIFO without creating records.

    Args:
        user_id (int): User ID who owns the purchases
        ticker (str): Stock ticker symbol
        shares_to_sell (float): Number of shares to preview selling

    Returns:
        dict: Preview information including:
            - assignments: List of dicts with purchase info and shares that would be assigned
            - total_cost_basis: Total cost basis for the shares
            - total_available: Total shares available
            - is_sufficient: Whether enough shares are available

    Raises:
        ValueError: If invalid parameters provided
    """
    if shares_to_sell <= 0:
        raise ValueError("shares_to_sell must be positive")

    # Get all purchases for this ticker ordered by purchase_date (FIFO)
    purchases = (Purchase.query
                .filter_by(user_id=user_id, ticker=ticker)
                .order_by(Purchase.purchase_date.asc())
                .all())

    if not purchases:
        return {
            'assignments': [],
            'total_cost_basis': 0.0,
            'total_available': 0.0,
            'is_sufficient': False,
            'error': f'No purchases found for ticker {ticker}'
        }

    # Calculate total shares available
    total_available = sum(p.shares_remaining for p in purchases)

    TOLERANCE = 0.0001
    is_sufficient = total_available >= shares_to_sell - TOLERANCE

    # Preview FIFO assignment
    assignments = []
    remaining_to_sell = shares_to_sell
    total_cost_basis = 0.0

    for purchase in purchases:
        if remaining_to_sell <= TOLERANCE:
            break

        available_from_purchase = purchase.shares_remaining

        if available_from_purchase <= TOLERANCE:
            continue

        # Determine how many shares would be assigned from this purchase
        shares_to_assign = min(remaining_to_sell, available_from_purchase)

        # Calculate cost basis for this assignment
        cost_basis = shares_to_assign * purchase.price_at_purchase
        total_cost_basis += cost_basis

        assignments.append({
            'purchase_id': purchase.id,
            'purchase_date': purchase.purchase_date.isoformat(),
            'price_at_purchase': purchase.price_at_purchase,
            'shares_available': available_from_purchase,
            'shares_to_assign': shares_to_assign,
            'cost_basis': cost_basis
        })

        remaining_to_sell -= shares_to_assign

    return {
        'assignments': assignments,
        'total_cost_basis': total_cost_basis,
        'total_available': total_available,
        'is_sufficient': is_sufficient,
        'shares_remaining_after': total_available - shares_to_sell if is_sufficient else None
    }
