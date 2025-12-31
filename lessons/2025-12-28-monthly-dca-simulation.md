# Lessons Learned: Monthly DCA SPY Simulation

**Date:** 2025-12-28
**Related Ticket:** N/A (user request)
**Commit:** cd9cf8b

## Problem Summary

User requested a new portfolio comparison showing what would have happened if their total invested amount was split evenly across calendar months and invested in SPY on the last trading day of each month. This provides a disciplined dollar-cost averaging (DCA) benchmark to compare against actual purchase timing.

## Approach Taken

### Design Philosophy
- **Virtual benchmark approach**: Treated "Monthly DCA SPY" as a calculated alternative rather than a ComparisonStock database entry
- **Ticker pattern**: Used `MONTHLY_DCA_SPY` as a virtual ticker to integrate seamlessly with existing comparison architecture
- **Equal monthly splits**: Total invested ÷ number of months = monthly investment amount

### Implementation Strategy

1. **Backend utility functions** (`stock_data.py`):
   - `get_last_trading_day_of_month()`: Walks backwards up to 5 days from month-end to find valid trading day
   - `generate_monthly_dca_dates()`: Generates list of (year, month, trading_date) tuples for date range

2. **Calculation functions** (`portfolio.py`):
   - `calculate_monthly_dca_spy()`: Summary endpoint calculation (total shares, current value, return %)
   - `calculate_monthly_dca_spy_history()`: Time-series calculation for chart (pre-computes shares by date)

3. **Integration points**:
   - Added to `get_portfolio_summary()` after existing alternatives
   - Added to `get_portfolio_history()` after existing alt_values
   - Reused same functions in guest.py via imports

4. **Frontend visualization**:
   - Purple color (#8b5cf6) for distinction from gray SPY benchmark
   - Dashed line pattern [5, 5] for visual differentiation
   - Label override to display "Monthly DCA SPY" instead of ticker

### Key Decisions

- **No database schema changes**: Leveraged existing `PriceCache` infrastructure
- **Performance optimization**: Reused already-fetched SPY price history in history endpoint
- **Guest mode parity**: Imported calculation functions rather than duplicating logic
- **Edge case handling**: Gracefully handles single purchase, incomplete months, missing data

## Key Lessons

1. **Virtual tickers for calculated benchmarks**: Not every comparison needs to be a ComparisonStock DB entry. Virtual tickers work well for derived calculations that use existing price data.

2. **Function reuse prevents divergence**: Importing `calculate_monthly_dca_spy()` in guest.py ensured identical logic between authenticated and guest modes. Duplicating the code would have created maintenance burden.

3. **Pre-computation for performance**: In `calculate_monthly_dca_spy_history()`, computing shares_by_date once before the date loop (rather than inside it) reduced O(M×D) operations to O(M+D) where M=months, D=dates.

4. **Trading day edge cases**: Month-end often falls on weekends/holidays. Walking backwards up to 5 days with weekday check ensures robust handling without complex holiday calendars.

5. **Chart.js styling patterns**: Dashed lines (`borderDash: [5, 5]`) and label overrides (`ticker === 'X' ? 'Display Name' : ticker`) are effective for distinguishing special benchmarks in existing chart infrastructure.

6. **Testing validates assumptions**: Playwright testing revealed that the feature worked correctly on first try, validating the design approach. Testing both viewports caught no issues, confirming responsive design principles were followed.

7. **Color choice matters**: Purple (#8b5cf6) provided clear visual distinction from existing benchmarks (gray SPY, green AAPL, blue META, orange GOOGL/NVDA/AMZN). Using a unique color family prevented confusion.

8. **Import circular dependency awareness**: Importing from `portfolio.py` into `guest.py` worked because guest.py doesn't import anything that portfolio.py depends on. If circular dependency existed, would need to extract shared logic to a utility module.

## Potential Improvements

1. **Configurable DCA parameters**: Future enhancement could allow users to choose:
   - DCA frequency (weekly, bi-weekly, monthly, quarterly)
   - DCA ticker (not just SPY, but any stock)
   - DCA start date (override first purchase month)

2. **Tooltip explanations**: Add help icon with explanation of what "Monthly DCA SPY" means for users unfamiliar with dollar-cost averaging.

3. **Performance caching**: For users with long purchase histories (10+ years), consider caching the monthly_dca calculation result for 1 hour to reduce repeated computations.

4. **Edge case: future purchases**: If user has future-dated purchases (rare but possible in test data), ensure DCA calculation handles this gracefully by only including months up to today.

5. **Accessibility**: Ensure chart legend colors are distinguishable for colorblind users (purple vs gray might be challenging for some types of colorblindness).

## Technical Patterns Worth Reusing

### Pattern: Virtual Ticker Integration
```python
# Add virtual benchmark to alternatives
virtual_benchmark = calculate_virtual_benchmark(purchases, current_prices)
if virtual_benchmark:
    alternatives.append(virtual_benchmark)
```

This pattern works for any calculated benchmark that doesn't require database persistence.

### Pattern: Date Utility with Fallback
```python
def get_last_trading_day_of_month(year: int, month: int) -> date:
    last_day = calendar.monthrange(year, month)[1]
    candidate_date = date(year, month, last_day)

    for i in range(5):  # Walk back up to 5 days
        check_date = candidate_date - timedelta(days=i)
        if check_date.weekday() >= 5:  # Skip weekends
            continue
        if is_trading_day(check_date):
            return check_date

    return None  # Graceful failure
```

Walking backwards with validation is more robust than hardcoded holiday calendars.

### Pattern: Pre-compute Before Loop
```python
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
    # ... use total_shares
```

Moving invariant calculations outside loops improves performance significantly for large datasets.

## Conclusion

The Monthly DCA SPY simulation feature demonstrates that calculated benchmarks can integrate seamlessly into existing comparison architecture without database schema changes. The virtual ticker pattern, combined with function reuse and pre-computation optimization, resulted in a maintainable, performant implementation that passed all tests on first deployment.

**Key Takeaway**: When adding new portfolio comparisons, ask: "Does this need to be stored in the database, or can it be calculated on-demand from existing data?" Calculated alternatives reduce schema complexity while maintaining flexibility.
