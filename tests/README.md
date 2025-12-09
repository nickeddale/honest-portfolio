# Honest Portfolio Test Suite

This directory contains the test suite for the Honest Portfolio Flask application.

## Overview

The test suite focuses on verifying the self-comparison price fix - a critical bug where self-comparisons (e.g., META purchase compared to META benchmark) were showing different prices because yfinance adjusted close prices change over time.

## Running Tests

```bash
# Activate virtual environment
source venv/bin/activate

# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_self_comparison.py

# Run with verbose output
pytest tests/test_self_comparison.py -v

# Run a specific test
pytest tests/test_self_comparison.py::TestSelfComparisonPriceFix::test_self_comparison_uses_stored_purchase_price
```

## Test Structure

### conftest.py
Provides pytest fixtures for:
- `app`: Flask test application with isolated database
- `client`: Flask test client for making HTTP requests
- `db_session`: Direct database session for test data setup
- `seed_comparison_stocks`: Seeds benchmark stocks (SPY, AAPL, META, GOOGL, NVDA, AMZN)
- `meta_purchase`: Creates a sample META purchase for testing
- `mock_stock_prices`: Mocks yfinance API calls to avoid external dependencies

### test_self_comparison.py
Contains 5 end-to-end tests:

1. **test_self_comparison_uses_stored_purchase_price**
   - Core test verifying the bug fix
   - Creates a META purchase with price $500
   - Adds a different cached price ($485) to simulate yfinance drift
   - Verifies that self-comparison uses stored price ($500), not cached price
   - Verifies difference_vs_actual is 0.0 for self-comparison

2. **test_different_ticker_comparison_uses_cached_price**
   - Ensures the fix doesn't break cross-ticker comparisons
   - Verifies AAPL comparison still uses cached/mocked prices

3. **test_self_comparison_with_no_cached_price**
   - Tests self-comparison when no PriceCache entry exists
   - Verifies stored purchase price is still used

4. **test_purchase_summary_data**
   - Sanity check for overall endpoint structure
   - Verifies purchase summary and actual performance data

5. **test_all_comparison_stocks_present**
   - Ensures all default benchmark stocks are included in response

## Key Features

- **Isolated Test Database**: Each test uses a temporary SQLite database
- **No External API Calls**: All yfinance calls are mocked
- **Comprehensive Coverage**: Tests both the fix and edge cases
- **Fast Execution**: All tests run in under 1 second

## Test Data

The mocked stock prices simulate realistic scenarios:
- Purchase date prices: META=$500, SPY=$450, AAPL=$180, etc.
- Current prices show 10-20% gains to test performance calculations
- Cached prices deliberately differ from purchase prices to test the fix

## Bug Context

The original bug occurred because:
1. When a purchase is made, we store the price at that time
2. Later, when comparing against benchmarks, we fetch historical prices
3. yfinance adjusted close prices can change over time due to splits, dividends, etc.
4. This caused self-comparisons (META vs META) to show non-zero differences

The fix ensures that when comparing a purchase to itself, we use the stored purchase price rather than fetching from the price cache or yfinance.
