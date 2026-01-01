# Stock Sales Database Schema

## Entity Relationship Diagram

```
┌─────────────────┐
│     users       │
│─────────────────│
│ id (PK)         │
│ email           │
│ name            │
│ ...             │
└─────────────────┘
        │
        │ 1:N
        ├──────────────────────────┐
        │                          │
        │                          │
        ▼                          ▼
┌─────────────────┐        ┌─────────────────┐
│   purchases     │        │     sales       │
│─────────────────│        │─────────────────│
│ id (PK)         │        │ id (PK)         │
│ user_id (FK)    │───┐    │ user_id (FK)    │
│ ticker          │   │    │ ticker          │
│ purchase_date   │   │    │ sale_date       │
│ shares_bought   │   │    │ shares_sold     │
│ price_at_purch. │   │    │ price_at_sale   │
│ amount          │   │    │ total_proceeds  │
│ ...             │   │    │ reinvest_purch  │◄───┐
└─────────────────┘   │    │   _id (FK)      │    │
        │             │    │ reinvested_amt  │    │
        │             │    │ cash_retained   │    │
        │ 1:N         │    └─────────────────┘    │
        │             │            │               │
        │             │            │ 1:N           │
        │             │            │               │
        │             │            ▼               │
        │             │    ┌─────────────────┐    │
        │             │    │ purchase_sale_  │    │
        │             │    │  assignments    │    │
        │             │    │─────────────────│    │
        │             │    │ id (PK)         │    │
        │             └───►│ purchase_id (FK)│    │
        │                  │ sale_id (FK)    │    │
        └──────────────────┤ shares_assigned │    │
           Optional        │ cost_basis      │    │
           Reinvestment    │ proceeds        │    │
           Link            │ realized_gain_  │    │
                           │   loss          │    │
                           └─────────────────┘    │
                                                  │
                                                  │
    Reinvestment Purchase ────────────────────────┘
    (Optional)
```

## Table Details

### sales
Tracks each stock sale transaction.

| Column | Type | Description |
|--------|------|-------------|
| id | Integer | Primary key |
| user_id | Integer | Foreign key to users.id |
| ticker | String(10) | Stock ticker symbol |
| sale_date | Date | Date when shares were sold |
| shares_sold | Float | Total number of shares sold |
| price_at_sale | Float | Sale price per share |
| total_proceeds | Float | Total sale proceeds (calculated) |
| reinvestment_purchase_id | Integer | Optional FK to purchases.id |
| reinvested_amount | Float | Amount reinvested (optional) |
| cash_retained | Float | Cash not reinvested (optional) |
| created_at | DateTime | Record creation timestamp |

**Indexes:**
- `ix_sales_user_id` on user_id
- `ix_sales_ticker` on ticker
- `ix_sales_sale_date` on sale_date
- `ix_sales_user_ticker` on (user_id, ticker)

### purchase_sale_assignments
Links purchases to sales using FIFO cost basis assignment. Each record represents shares from one purchase used in one sale.

| Column | Type | Description |
|--------|------|-------------|
| id | Integer | Primary key |
| purchase_id | Integer | Foreign key to purchases.id |
| sale_id | Integer | Foreign key to sales.id |
| shares_assigned | Float | Shares from this purchase used in sale |
| cost_basis | Float | Cost basis for assigned shares |
| proceeds | Float | Proceeds for assigned shares |
| realized_gain_loss | Float | Gain/loss (proceeds - cost_basis) |

**Indexes:**
- `ix_psa_purchase_id` on purchase_id
- `ix_psa_sale_id` on sale_id

### purchases (updated)
Added relationship to track sale assignments.

**New Properties:**
- `shares_sold` (computed) - Sum of shares_assigned across all assignments
- `shares_remaining` (computed) - shares_bought - shares_sold

**New Relationship:**
- `sale_assignments` - One-to-many with PurchaseSaleAssignment

### users (updated)

**New Relationship:**
- `sales` - One-to-many with Sale

## Cascade Delete Behavior

```
DELETE User
  ├─► Deletes all Purchases
  │   └─► Deletes all PurchaseSaleAssignments for those purchases
  │
  └─► Deletes all Sales
      └─► Deletes all PurchaseSaleAssignments for those sales

DELETE Purchase
  └─► Deletes all PurchaseSaleAssignments for that purchase
      └─► Orphans the Sale if no other assignments exist
          (Sale record remains but has no cost basis data)

DELETE Sale
  └─► Deletes all PurchaseSaleAssignments for that sale
      └─► Purchases remain with their shares_remaining recalculated
```

## FIFO Assignment Flow

When a sale is created with `create_sale_with_fifo()`:

1. Query purchases for ticker ordered by `purchase_date ASC`
2. For each purchase (oldest first):
   ```
   available = purchase.shares_bought - purchase.shares_sold
   assign = min(remaining_to_sell, available)

   Create PurchaseSaleAssignment:
     - shares_assigned = assign
     - cost_basis = assign * purchase.price_at_purchase
     - proceeds = assign * sale.price_at_sale
     - realized_gain_loss = proceeds - cost_basis

   remaining_to_sell -= assign
   ```
3. Continue until all shares assigned or purchases exhausted

### Example FIFO Scenario

**Initial State:**
```
Purchase 1: 2024-01-15, 100 shares @ $50 = $5,000
Purchase 2: 2024-03-20, 50 shares @ $60 = $3,000
Purchase 3: 2024-05-10, 75 shares @ $55 = $4,125

Total: 225 shares, $12,125 invested
```

**Sale Transaction:**
```
Sell 120 shares on 2024-06-01 @ $70
```

**FIFO Assignments Created:**
```
Assignment 1:
  purchase_id: 1 (oldest)
  shares_assigned: 100 (all from Purchase 1)
  cost_basis: 100 * $50 = $5,000
  proceeds: 100 * $70 = $7,000
  realized_gain_loss: $2,000 gain

Assignment 2:
  purchase_id: 2 (next oldest)
  shares_assigned: 20 (partial from Purchase 2)
  cost_basis: 20 * $60 = $1,200
  proceeds: 20 * $70 = $1,400
  realized_gain_loss: $200 gain

Total Sale:
  shares_sold: 120
  total_proceeds: $8,400
  total_gain: $2,200
```

**Remaining Positions After Sale:**
```
Purchase 1: 0 shares remaining (fully sold)
Purchase 2: 30 shares remaining @ $60 cost basis
Purchase 3: 75 shares remaining @ $55 cost basis

Total: 105 shares, $5,925 invested
```

## Reinvestment Tracking

After a sale, proceeds can be linked to a new purchase:

```python
# Sale generated $8,400 proceeds
# User reinvests $8,000 into new purchase

link_sale_to_reinvestment(
    sale_id=sale.id,
    purchase_id=new_purchase.id,
    reinvested_amount=8000.0
)

# Sale record updated:
# reinvestment_purchase_id = new_purchase.id
# reinvested_amount = $8,000
# cash_retained = $400
```

This creates a bidirectional link:
- Sale → Reinvestment Purchase (via reinvestment_purchase_id)
- Reinvestment Purchase ← Sale (via backref 'reinvested_from_sale')

## Query Examples

### Get all sales for a user with assignments
```python
sales = Sale.query.filter_by(user_id=user_id).all()

for sale in sales:
    print(f"Sale: {sale.shares_sold} {sale.ticker} @ ${sale.price_at_sale}")
    for assignment in sale.purchase_assignments:
        print(f"  From purchase {assignment.purchase_id}: "
              f"{assignment.shares_assigned} shares, "
              f"gain/loss: ${assignment.realized_gain_loss}")
```

### Calculate total realized gains/losses for a ticker
```python
assignments = (PurchaseSaleAssignment.query
               .join(Sale)
               .filter(Sale.user_id == user_id, Sale.ticker == ticker)
               .all())

total_realized = sum(a.realized_gain_loss for a in assignments)
```

### Find purchases with remaining shares
```python
purchases = Purchase.query.filter_by(user_id=user_id, ticker=ticker).all()
available_purchases = [p for p in purchases if p.shares_remaining > 0]
```

### Get reinvestment chain
```python
# Find sale that funded a purchase
purchase = Purchase.query.get(purchase_id)
funding_sale = Sale.query.filter_by(
    reinvestment_purchase_id=purchase_id
).first()

if funding_sale:
    print(f"Purchase funded by sale of {funding_sale.ticker}")
```
