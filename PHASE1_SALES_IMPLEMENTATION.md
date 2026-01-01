# Phase 1: Stock Sales Implementation Summary

## Overview
Phase 1 adds stock sales tracking with FIFO (First In, First Out) cost basis assignment and reinvestment tracking to the Honest Portfolio application.

## Implementation Date
December 31, 2025

## Files Modified

### 1. `/Users/nickdale/code/honest-portfolio/app/models.py`

#### Added Models

**Sale Model** (`sales` table)
- `id`: Integer primary key
- `user_id`: Foreign key to users table
- `ticker`: String(10) - stock symbol
- `sale_date`: Date - when the sale occurred
- `shares_sold`: Float - number of shares sold
- `price_at_sale`: Float - sale price per share
- `total_proceeds`: Float - total sale proceeds (shares_sold * price_at_sale)
- `reinvestment_purchase_id`: Foreign key to purchases table (nullable)
- `reinvested_amount`: Float (nullable) - amount reinvested from proceeds
- `cash_retained`: Float (nullable) - proceeds not reinvested
- `created_at`: DateTime - record creation timestamp
- **Relationships**:
  - `purchase_assignments` - one-to-many with PurchaseSaleAssignment (cascade delete)
  - `reinvestment_purchase` - many-to-one with Purchase (optional reinvestment link)
  - `user` - many-to-one with User (backref)

**PurchaseSaleAssignment Model** (`purchase_sale_assignments` table)
- `id`: Integer primary key
- `purchase_id`: Foreign key to purchases table
- `sale_id`: Foreign key to sales table
- `shares_assigned`: Float - shares from this purchase used in the sale
- `cost_basis`: Float - cost basis for the assigned shares
- `proceeds`: Float - proceeds for the assigned shares
- `realized_gain_loss`: Float - calculated gain/loss (proceeds - cost_basis)
- **Relationships**:
  - `purchase` - many-to-one with Purchase (backref)
  - `sale` - many-to-one with Sale (backref)

#### Updated Models

**Purchase Model**
- Added relationship: `sale_assignments` - one-to-many with PurchaseSaleAssignment (cascade delete)
- Added property: `shares_sold` - calculates total shares sold from this purchase
- Added property: `shares_remaining` - calculates shares not yet sold (shares_bought - shares_sold)
- Updated `to_dict()` method to include `shares_remaining`

**User Model**
- Added relationship: `sales` - one-to-many with Sale (cascade delete)

## Files Created

### 2. `/Users/nickdale/code/honest-portfolio/app/services/sale_service.py`

Comprehensive service module for handling stock sales with FIFO logic.

#### Functions

**create_sale_with_fifo(user_id, ticker, sale_date, shares_sold, price_at_sale)**
- Creates a sale record and automatically assigns shares using FIFO method
- Validates sufficient shares are available before processing
- Iterates through purchases ordered by purchase_date ASC (oldest first)
- Creates PurchaseSaleAssignment records for each purchase used
- Calculates cost_basis, proceeds, and realized_gain_loss for each assignment
- Uses tolerance (0.0001) for floating point comparisons
- Returns: Created Sale object
- Raises:
  - `InsufficientSharesError` if not enough shares available
  - `ValueError` for invalid parameters

**link_sale_to_reinvestment(sale_id, purchase_id, reinvested_amount)**
- Links a sale to a reinvestment purchase
- Updates sale with reinvestment_purchase_id, reinvested_amount, and cash_retained
- Validates reinvested_amount doesn't exceed total_proceeds
- Returns: Updated Sale object
- Raises: `ValueError` for invalid sale/purchase IDs or amounts

**preview_fifo_assignment(user_id, ticker, shares_to_sell)**
- Previews FIFO assignment without creating database records
- Useful for validation and UI display before executing sale
- Returns dictionary with:
  - `assignments`: List of purchase assignments with details
  - `total_cost_basis`: Sum of cost basis across all assignments
  - `total_available`: Total shares available for the ticker
  - `is_sufficient`: Boolean if enough shares exist
  - `shares_remaining_after`: Shares remaining after hypothetical sale
  - `error`: Error message if no purchases found

#### Custom Exception

**InsufficientSharesError**
- Extends ValueError
- Raised when attempting to sell more shares than available

### 3. `/Users/nickdale/code/honest-portfolio/migrations/versions/001_add_sales_tables.py`

Database migration file in Alembic format (compatible with Flask-Migrate if installed in the future).

#### Tables Created

**sales**
- All Sale model columns
- Foreign keys to users and purchases tables
- Indexes:
  - `ix_sales_user_id` on user_id
  - `ix_sales_ticker` on ticker
  - `ix_sales_sale_date` on sale_date
  - `ix_sales_user_ticker` on (user_id, ticker) composite

**purchase_sale_assignments**
- All PurchaseSaleAssignment model columns
- Foreign keys to purchases and sales tables
- Indexes:
  - `ix_psa_purchase_id` on purchase_id
  - `ix_psa_sale_id` on sale_id

#### Migration Functions
- `upgrade()`: Creates tables and indexes
- `downgrade()`: Drops tables and indexes in correct order

### 4. `/Users/nickdale/code/honest-portfolio/migrations/README.md`

Documentation for the migrations system explaining:
- Current migration status (manual, no Flask-Migrate)
- Three options for applying migrations
- Migration file structure
- Notes on compatibility and future Flask-Migrate support

## Implementation Details

### FIFO Algorithm
The FIFO (First In, First Out) algorithm ensures tax-compliant cost basis assignment:

1. Query all purchases for the ticker ordered by `purchase_date ASC`
2. For each purchase (oldest first):
   - Calculate `shares_remaining` (shares_bought - shares already sold)
   - Assign minimum of (remaining_to_sell, shares_remaining)
   - Calculate cost_basis = shares_assigned * purchase.price_at_purchase
   - Calculate proceeds = shares_assigned * price_at_sale
   - Calculate realized_gain_loss = proceeds - cost_basis
   - Create PurchaseSaleAssignment record
   - Decrement remaining_to_sell
3. Validate all shares were assigned (within tolerance)

### Floating Point Handling
Uses tolerance of 0.0001 for all floating point comparisons to avoid precision issues:
```python
TOLERANCE = 0.0001
if total_available < shares_sold - TOLERANCE:
    raise InsufficientSharesError(...)
```

### Cascade Behavior
All foreign key relationships properly configured with cascade delete:
- Deleting a User cascades to delete all Sales
- Deleting a Sale cascades to delete all PurchaseSaleAssignments
- Deleting a Purchase cascades to delete all PurchaseSaleAssignments

### Database Application

Since Flask-Migrate is not installed, the new tables will be created automatically when the application starts via `db.create_all()` in the app factory:

```python
# In app/__init__.py line 142-145
with app.app_context():
    db.create_all()
    from app.models import seed_comparison_stocks
    seed_comparison_stocks()
```

Simply restart the application and the new tables will be created.

## Validation Completed

All requirements from Phase 1 specification have been implemented:

- [x] Sale model with all required fields and relationships
- [x] PurchaseSaleAssignment model
- [x] Purchase model updates (shares_sold, shares_remaining properties)
- [x] User model sales relationship
- [x] sale_service.py with FIFO logic
- [x] create_sale_with_fifo function
- [x] link_sale_to_reinvestment function
- [x] preview_fifo_assignment function
- [x] Database migration file
- [x] Proper foreign key cascade behavior
- [x] Floating point tolerance handling (0.0001)
- [x] Strict FIFO ordering by purchase_date ASC
- [x] Comprehensive error handling

## Next Steps (Future Phases)

Phase 1 provides the data model and core business logic. Future phases should include:

1. **API Endpoints** - Create Flask blueprints for:
   - POST /api/sales - Create a new sale
   - GET /api/sales - List user's sales
   - GET /api/sales/{id} - Get sale details with assignments
   - DELETE /api/sales/{id} - Delete a sale
   - POST /api/sales/{id}/reinvestment - Link to reinvestment
   - GET /api/sales/preview - Preview FIFO assignment

2. **Frontend UI** - Add sales management interface:
   - Sale entry form with ticker/date/shares/price
   - FIFO preview before sale execution
   - Sales history table
   - Reinvestment linking interface
   - Portfolio summary with realized gains/losses

3. **Reporting** - Add analytics:
   - Total realized gains/losses by year
   - Tax reporting exports (CSV, PDF)
   - Cost basis reports
   - Reinvestment tracking visualization

4. **Testing** - Add comprehensive test coverage:
   - Unit tests for sale_service functions
   - Integration tests for API endpoints
   - Edge case tests (fractional shares, same-day sales, etc.)

## Usage Examples

### Example 1: Create a Sale with FIFO

```python
from app.services.sale_service import create_sale_with_fifo
from datetime import date

# User has these purchases:
# Purchase 1: 2024-01-15, 10 shares AAPL @ $150
# Purchase 2: 2024-03-20, 5 shares AAPL @ $160

# Sell 12 shares on 2024-06-01 @ $170
sale = create_sale_with_fifo(
    user_id=1,
    ticker='AAPL',
    sale_date=date(2024, 6, 1),
    shares_sold=12.0,
    price_at_sale=170.0
)

# Result: Two assignments created
# Assignment 1: 10 shares from Purchase 1
#   cost_basis = 10 * $150 = $1,500
#   proceeds = 10 * $170 = $1,700
#   realized_gain_loss = $200
# Assignment 2: 2 shares from Purchase 2
#   cost_basis = 2 * $160 = $320
#   proceeds = 2 * $170 = $340
#   realized_gain_loss = $20
# Total: $220 gain
```

### Example 2: Preview FIFO Before Sale

```python
from app.services.sale_service import preview_fifo_assignment

preview = preview_fifo_assignment(
    user_id=1,
    ticker='AAPL',
    shares_to_sell=12.0
)

# Returns:
# {
#     'assignments': [
#         {
#             'purchase_id': 1,
#             'purchase_date': '2024-01-15',
#             'price_at_purchase': 150.0,
#             'shares_available': 10.0,
#             'shares_to_assign': 10.0,
#             'cost_basis': 1500.0
#         },
#         {
#             'purchase_id': 2,
#             'purchase_date': '2024-03-20',
#             'price_at_purchase': 160.0,
#             'shares_available': 5.0,
#             'shares_to_assign': 2.0,
#             'cost_basis': 320.0
#         }
#     ],
#     'total_cost_basis': 1820.0,
#     'total_available': 15.0,
#     'is_sufficient': True,
#     'shares_remaining_after': 3.0
# }
```

### Example 3: Link Sale to Reinvestment

```python
from app.services.sale_service import link_sale_to_reinvestment

# After creating a sale with $2,040 proceeds
# User reinvests $1,800 into a new purchase

updated_sale = link_sale_to_reinvestment(
    sale_id=sale.id,
    purchase_id=new_purchase.id,
    reinvested_amount=1800.0
)

# Sale record updated with:
# reinvestment_purchase_id = new_purchase.id
# reinvested_amount = $1,800
# cash_retained = $240
```

## File Locations Summary

```
/Users/nickdale/code/honest-portfolio/
├── app/
│   ├── models.py                          # MODIFIED - Added Sale, PurchaseSaleAssignment, updated Purchase & User
│   └── services/
│       └── sale_service.py                # NEW - FIFO logic and sale management
├── migrations/
│   ├── README.md                          # NEW - Migration documentation
│   └── versions/
│       └── 001_add_sales_tables.py        # NEW - Database migration
└── PHASE1_SALES_IMPLEMENTATION.md         # NEW - This summary document
```
