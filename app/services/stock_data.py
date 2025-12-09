import yfinance as yf
from datetime import datetime, timedelta
from app import db
from app.models import PriceCache

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

        # Cache the price
        cache_entry = PriceCache(ticker=ticker, date=date, close_price=close_price)
        db.session.add(cache_entry)
        db.session.commit()

        return close_price
    except Exception as e:
        print(f"Error fetching price for {ticker} on {date}: {e}")
        return None

def get_current_price(ticker: str) -> float:
    """Get the current/latest price for a ticker."""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        return info.get('regularMarketPrice') or info.get('previousClose')
    except Exception as e:
        print(f"Error fetching current price for {ticker}: {e}")
        return None

def get_price_history(ticker: str, start_date, end_date=None) -> dict:
    """Get price history from start_date to end_date (or today)."""
    try:
        stock = yf.Ticker(ticker)
        if end_date is None:
            end_date = datetime.now().date()

        hist = stock.history(start=start_date, end=end_date + timedelta(days=1))

        # Return as dict of date -> price
        prices = {}
        for idx, row in hist.iterrows():
            prices[idx.date()] = float(row['Close'])

        return prices
    except Exception as e:
        print(f"Error fetching price history for {ticker}: {e}")
        return {}
