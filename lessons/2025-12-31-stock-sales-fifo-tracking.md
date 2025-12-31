# Lessons Learned: Stock Sales with FIFO Cost Basis Tracking

**Date:** 2025-12-31
**Related Ticket:** N/A (exploratory feature request)
**Commit:** 3f325b0

## Problem Summary

The portfolio tracker needed a way to handle stock sales while:
- Maintaining accurate cost basis for tax reporting (FIFO)
- Distinguishing between realized (sold) and unrealized (held) gains
- Tracking reinvestment flows (selling one stock to buy another)
- Preserving the core "opportunity cost" comparison methodology

The challenge was designing a system that could track partial sales across multiple purchase lots while keeping analytics calculations simple and performant.

## Approach Taken

**Data Model Design:**
- Created a `Sale` model for sale transactions
- Created a `PurchaseSaleAssignment` junction table to implement FIFO assignment
- Each sale can have multiple assignments (selling from multiple purchase lots)
- Added computed properties (`shares_remaining`) to Purchase model for easy querying

**FIFO Implementation:**
- Centralized logic in `sale_service.py` with `create_sale_with_fifo()`
- Algorithm iterates through purchases ordered by `purchase_date ASC`
- Assigns shares from oldest purchases first until all sold shares are accounted for
- Each assignment tracks: shares, cost basis, proceeds, and realized gain/loss

**Frontend Integration:**
- Added 4th tab "Record Sale" to match existing UI patterns
- Real-time calculations for proceeds and cash retained
- FIFO preview fetched from backend before submission
- Visual indicators (badges, X/Y shares remaining) for partial sales

**Key Design Decisions:**
1. **Auto-assignment vs manual**: Chose automatic FIFO over letting users pick lots to match IRS default and keep UX simple
2. **Reinvestment tracking**: Optional linking to support "sold X, bought Y" workflows
3. **Realized/unrealized split**: Displayed separately in summary cards to show both actual cash gains and paper gains
4. **Proportional benchmarks**: When user sells, benchmarks also "sell" proportionally to maintain fair comparison

## Key Lessons

- **Computed properties are powerful**: Using `@property` for `shares_remaining` kept queries simple while hiding complexity of FIFO calculations
- **Service layer pattern**: Centralizing FIFO logic in `sale_service.py` made it testable and reusable (API + future batch operations)
- **Junction tables for assignments**: The `PurchaseSaleAssignment` model cleanly handles many-to-many with additional data (cost basis, realized gain)
- **Validation is critical for sales**: Must check sufficient shares available, trading day, and prevent selling from future
- **Real-time calculations enhance UX**: Auto-calculating proceeds and showing FIFO preview prevents user errors
- **Existing patterns speed development**: Following the purchase form's tabbed structure made the sale UI feel native

## Technical Insights

**Database Design:**
```python
# Clean separation of concerns
Sale           # Transaction record
├── purchase_assignments  # FIFO tracking (many)
└── reinvestment_purchase # Optional link (one)

Purchase
└── sale_assignments  # What's been sold
```

**Analytics Pattern:**
```python
# Realized: sum of completed sales
realized_gains = sum(assignment.realized_gain_loss
                    for sale in user.sales
                    for assignment in sale.purchase_assignments)

# Unrealized: current value - remaining cost basis
unrealized_gains = sum(purchase.shares_remaining * current_price
                      - purchase.shares_remaining * purchase.price_at_purchase)
```

**Performance Considerations:**
- FIFO algorithm is O(n) where n = number of purchases for that ticker
- Pre-loading assignments via `db.joinedload()` avoids N+1 queries
- Indexes on `(user_id, ticker)` and `sale_date` keep lookups fast

## Potential Improvements

1. **Batch sale support**: Allow selling shares across multiple tickers in one transaction (portfolio rebalancing)
2. **Tax lot optimization**: Offer "sell highest cost basis first" option to minimize short-term capital gains
3. **Wash sale detection**: Flag sales where same security is repurchased within 30 days
4. **Export to tax software**: Generate CSV/JSON with cost basis details for Schedule D
5. **Sale reversal/correction**: Add undo functionality for accidental sales
6. **Performance caching**: Cache realized gains sum to avoid recalculation on every page load
7. **Mobile optimization**: Add swipe gestures for quick sale entry on mobile devices

## What Worked Well

- **Incremental implementation**: Building backend → API → frontend in phases allowed thorough testing at each step
- **Playwright testing**: Caught the weekend date validation bug before it reached users
- **Documentation**: Creating schema diagrams and usage examples made the FIFO logic clear
- **Existing infrastructure**: Stock price caching and yfinance integration "just worked" for sale prices

## Gotchas to Watch

- **Floating point precision**: Use tolerance (0.0001) when comparing shares for "fully sold" checks
- **Cascade deletes**: Must configure `cascade='all, delete-orphan'` on relationships to prevent orphaned assignments
- **Date validation**: Weekend/holiday validation is critical - users often enter sales on non-trading days
- **Reinvestment edge cases**: What if user sells and reinvests in multiple different stocks? Current design supports one-to-one only
