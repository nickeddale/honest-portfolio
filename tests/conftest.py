"""
Pytest configuration and fixtures for the Honest Portfolio test suite.
"""
import pytest
import tempfile
import os
from datetime import datetime, date
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS


# Import without triggering execution
from app import db


@pytest.fixture(scope='function')
def app(monkeypatch):
    """Create and configure a test Flask application instance."""
    # Import models here to access them
    from app.models import ComparisonStock, Purchase, PriceCache

    # Monkey-patch the seed function BEFORE importing create_app logic
    # This prevents auto-seeding during create_app()
    import app.models
    monkeypatch.setattr(app.models, 'seed_comparison_stocks', lambda: None)

    # Create a temporary database file
    db_fd, db_path = tempfile.mkstemp()

    # Now create the app - manually without calling create_app() to avoid seeding
    test_app = Flask(__name__, static_folder='../app/static')
    test_app.config.update({
        'TESTING': True,
        'SECRET_KEY': 'test-secret-key',
        'SQLALCHEMY_DATABASE_URI': f'sqlite:///{db_path}',
        'SQLALCHEMY_TRACK_MODIFICATIONS': False,
    })

    # Initialize extensions
    db.init_app(test_app)
    CORS(test_app)

    # Register blueprints
    from app.routes.purchases import purchases_bp
    from app.routes.portfolio import portfolio_bp
    from app.routes.stocks import stocks_bp

    test_app.register_blueprint(purchases_bp, url_prefix='/api')
    test_app.register_blueprint(portfolio_bp, url_prefix='/api')
    test_app.register_blueprint(stocks_bp, url_prefix='/api')

    # Create the database and tables (without seeding)
    with test_app.app_context():
        db.create_all()

    yield test_app

    # Cleanup
    with test_app.app_context():
        db.session.remove()
        db.drop_all()

    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture(scope='function')
def client(app):
    """Create a test client for the Flask application."""
    return app.test_client()


@pytest.fixture(scope='function')
def db_session(app):
    """Provide a database session for direct database manipulation in tests."""
    with app.app_context():
        yield db.session


@pytest.fixture(scope='function')
def seed_comparison_stocks(app, db_session):
    """Seed the database with default comparison stocks including META."""
    from app.models import ComparisonStock

    comparison_stocks_data = [
        ('SPY', 'S&P 500 ETF'),
        ('AAPL', 'Apple'),
        ('META', 'Meta'),
        ('GOOGL', 'Alphabet/Google'),
        ('NVDA', 'Nvidia'),
        ('AMZN', 'Amazon'),
    ]

    stocks = []
    for ticker, name in comparison_stocks_data:
        stock = ComparisonStock(ticker=ticker, name=name, is_default=True)
        db_session.add(stock)
        stocks.append(stock)

    db_session.commit()
    return stocks


@pytest.fixture(scope='function')
def meta_purchase(app, db_session, seed_comparison_stocks):
    """Create a META purchase with a known price for testing."""
    from app.models import Purchase

    purchase_date = date(2024, 1, 15)  # A known trading day
    purchase_price = 500.00
    purchase_amount = 10000.00
    shares_bought = purchase_amount / purchase_price  # 20.0 shares

    purchase = Purchase(
        ticker='META',
        purchase_date=purchase_date,
        amount=purchase_amount,
        shares_bought=shares_bought,
        price_at_purchase=purchase_price
    )

    db_session.add(purchase)
    db_session.commit()

    return purchase


@pytest.fixture(scope='function', autouse=False)
def mock_stock_prices(mocker):
    """
    Mock the stock_data service functions to avoid external yfinance calls.
    Returns the mocker instance for additional customization in tests.

    This fixture should be used by tests to avoid real yfinance API calls.
    """
    # Mock validate_ticker to always return True for test tickers
    mocker.patch('app.services.stock_data.validate_ticker', return_value=True)

    # Mock is_trading_day to return True for test dates
    mocker.patch('app.services.stock_data.is_trading_day', return_value=True)

    # Mock get_price_on_date with realistic prices
    def mock_get_price_on_date(ticker, date_obj):
        prices = {
            'META': 500.00,   # Purchase date price
            'SPY': 450.00,
            'AAPL': 180.00,
            'GOOGL': 140.00,
            'NVDA': 500.00,
            'AMZN': 150.00,
        }
        return prices.get(ticker, 100.00)

    mocker.patch('app.services.stock_data.get_price_on_date', side_effect=mock_get_price_on_date)

    # Mock get_current_price with different prices (simulating price changes)
    def mock_get_current_price(ticker):
        current_prices = {
            'META': 550.00,   # 10% gain
            'SPY': 495.00,    # 10% gain
            'AAPL': 198.00,   # 10% gain
            'GOOGL': 154.00,  # 10% gain
            'NVDA': 600.00,   # 20% gain
            'AMZN': 165.00,   # 10% gain
        }
        return current_prices.get(ticker, 110.00)

    mocker.patch('app.services.stock_data.get_current_price', side_effect=mock_get_current_price)

    # Mock get_price_history to return empty dict (not needed for basic comparison test)
    mocker.patch('app.services.stock_data.get_price_history', return_value={})

    return mocker
