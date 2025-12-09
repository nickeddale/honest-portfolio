from app import db
from datetime import datetime

class Purchase(db.Model):
    __tablename__ = 'purchases'

    id = db.Column(db.Integer, primary_key=True)
    ticker = db.Column(db.String(10), nullable=False)
    purchase_date = db.Column(db.Date, nullable=False)
    amount = db.Column(db.Float, nullable=False)
    shares_bought = db.Column(db.Float, nullable=False)
    price_at_purchase = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'ticker': self.ticker,
            'purchase_date': self.purchase_date.isoformat(),
            'amount': self.amount,
            'shares_bought': self.shares_bought,
            'price_at_purchase': self.price_at_purchase,
            'created_at': self.created_at.isoformat()
        }

class ComparisonStock(db.Model):
    __tablename__ = 'comparison_stocks'

    id = db.Column(db.Integer, primary_key=True)
    ticker = db.Column(db.String(10), nullable=False, unique=True)
    name = db.Column(db.String(100), nullable=False)
    is_default = db.Column(db.Boolean, default=False)

    def to_dict(self):
        return {
            'id': self.id,
            'ticker': self.ticker,
            'name': self.name,
            'is_default': self.is_default
        }

class PriceCache(db.Model):
    __tablename__ = 'price_cache'

    id = db.Column(db.Integer, primary_key=True)
    ticker = db.Column(db.String(10), nullable=False)
    date = db.Column(db.Date, nullable=False)
    close_price = db.Column(db.Float, nullable=False)
    fetched_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('ticker', 'date', name='unique_ticker_date'),
    )

def seed_comparison_stocks():
    """Seed the default comparison stocks if they don't exist."""
    default_stocks = [
        ('SPY', 'S&P 500 ETF'),
        ('AAPL', 'Apple'),
        ('META', 'Meta'),
        ('GOOGL', 'Alphabet/Google'),
        ('NVDA', 'Nvidia'),
        ('AMZN', 'Amazon'),
    ]

    for ticker, name in default_stocks:
        existing = ComparisonStock.query.filter_by(ticker=ticker).first()
        if not existing:
            stock = ComparisonStock(ticker=ticker, name=name, is_default=True)
            db.session.add(stock)

    db.session.commit()
