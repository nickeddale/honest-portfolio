import yfinance as yf
import math
from datetime import datetime, timedelta
from app import db
from app.models import PriceCache

# Module-level cache for current prices
_price_cache = {}  # {ticker: price}

def invalidate_price_cache():
    """Clear the in-memory price cache."""
    global _price_cache
    _price_cache.clear()

def get_current_prices(tickers: list) -> dict:
    """
    Batch fetch current prices for multiple tickers.

    Args:
        tickers: List of ticker symbols

    Returns:
        Dict of {ticker: price}
    """
    if not tickers:
        return {}

    try:
        # Fetch all tickers at once using yfinance download
        data = yf.download(tickers, period='1d', progress=False, group_by='ticker')

        prices = {}

        # Handle single ticker vs multiple tickers
        if len(tickers) == 1:
            ticker = tickers[0]
            if not data.empty and 'Close' in data.columns:
                price = float(data['Close'].iloc[-1])
                if not math.isnan(price):
                    prices[ticker] = price
                    _price_cache[ticker] = price
        else:
            # Multiple tickers - data is grouped by ticker
            for ticker in tickers:
                try:
                    if ticker in data.columns.get_level_values(0):
                        ticker_data = data[ticker]
                        if not ticker_data.empty and 'Close' in ticker_data.columns:
                            price = float(ticker_data['Close'].iloc[-1])
                            if not math.isnan(price):
                                prices[ticker] = price
                                _price_cache[ticker] = price
                except Exception as e:
                    print(f"Error extracting price for {ticker}: {e}")

        return prices

    except Exception as e:
        print(f"Error batch fetching prices: {e}")
        return {}

def validate_ticker(ticker: str) -> bool:
    """Check if a ticker symbol is valid."""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        return info.get('regularMarketPrice') is not None or info.get('previousClose') is not None
    except Exception:
        return False

def is_trading_day(date) -> bool:
    """Check if a date is a valid trading day (not weekend)."""
    # Basic check: weekday (0=Monday, 6=Sunday)
    if date.weekday() >= 5:
        return False

    # Try to get price for that date - if no data, it's likely a holiday
    # We use SPY as a proxy since it's always traded on market days
    try:
        stock = yf.Ticker('SPY')
        end_date = date + timedelta(days=1)
        hist = stock.history(start=date, end=end_date)
        return len(hist) > 0
    except Exception:
        return False

def get_price_on_date(ticker: str, date) -> float:
    """Get the closing price for a ticker on a specific date. Uses cache."""
    # Check cache first
    cached = PriceCache.query.filter_by(ticker=ticker, date=date).first()
    if cached:
        return cached.close_price

    try:
        stock = yf.Ticker(ticker)
        end_date = date + timedelta(days=1)
        hist = stock.history(start=date, end=end_date)

        if hist.empty:
            return None

        close_price = float(hist['Close'].iloc[0])
        if math.isnan(close_price):
            return None

        # Cache the price
        cache_entry = PriceCache(ticker=ticker, date=date, close_price=close_price)
        db.session.add(cache_entry)
        db.session.commit()

        return close_price
    except Exception as e:
        print(f"Error fetching price for {ticker} on {date}: {e}")
        return None

def get_current_price(ticker: str) -> float:
    """
    Get the current/latest price for a ticker.
    Uses in-memory cache if available, otherwise fetches from yfinance.
    """
    # Check cache first
    if ticker in _price_cache:
        return _price_cache[ticker]

    # Not cached - fetch single ticker
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        price = info.get('regularMarketPrice') or info.get('previousClose')

        # Cache the result
        if price is not None:
            _price_cache[ticker] = price

        return price
    except Exception as e:
        print(f"Error fetching current price for {ticker}: {e}")
        return None

def get_price_history(ticker: str, start_date, end_date=None) -> dict:
    """
    Get price history from start_date to end_date (or today).
    Checks PriceCache database first, fetches missing dates from yfinance,
    and persists new data to database.
    """
    try:
        if end_date is None:
            end_date = datetime.now().date()

        # Check cache for existing prices
        cached_prices = PriceCache.query.filter(
            PriceCache.ticker == ticker,
            PriceCache.date >= start_date,
            PriceCache.date <= end_date
        ).all()

        # Build dict of cached prices
        prices = {cache.date: cache.close_price for cache in cached_prices}

        # Determine if we need to fetch from yfinance
        # Generate all dates we need (only trading days matter, but we'll check all)
        date_range = (end_date - start_date).days + 1
        all_dates_needed = {start_date + timedelta(days=i) for i in range(date_range)}
        cached_dates = set(prices.keys())
        missing_dates = all_dates_needed - cached_dates

        # If we have some missing dates, fetch from yfinance
        if missing_dates:
            stock = yf.Ticker(ticker)
            hist = stock.history(start=start_date, end=end_date + timedelta(days=1))

            if not hist.empty:
                # Prepare bulk insert data
                new_cache_entries = []

                for idx, row in hist.iterrows():
                    date = idx.date()
                    close_price = float(row['Close'])

                    # Skip NaN values
                    if math.isnan(close_price):
                        continue

                    # Only add if not already cached
                    if date not in cached_dates:
                        prices[date] = close_price

                        # Prepare for bulk insert
                        new_cache_entries.append({
                            'ticker': ticker,
                            'date': date,
                            'close_price': close_price
                        })

                # Bulk insert new cache entries
                if new_cache_entries:
                    db.session.bulk_insert_mappings(PriceCache, new_cache_entries)
                    db.session.commit()

        return prices

    except Exception as e:
        print(f"Error fetching price history for {ticker}: {e}")
        return {}
