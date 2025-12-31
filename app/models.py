from app import db
from datetime import datetime
from sqlalchemy import Index
from flask_login import UserMixin


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=True)
    name = db.Column(db.String(100), nullable=False)
    profile_picture = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, default=datetime.utcnow)
    is_premium = db.Column(db.Boolean, default=False, nullable=False)
    premium_since = db.Column(db.DateTime, nullable=True)

    # Relationships
    auth_accounts = db.relationship("UserAuthAccount", backref="user",
                                    lazy=True, cascade="all, delete-orphan")
    purchases = db.relationship('Purchase', backref='user',
                               lazy=True, cascade='all, delete-orphan')
    sales = db.relationship('Sale', backref='user',
                           lazy=True, cascade='all, delete-orphan')

    def to_dict_public(self):
        """Public user info (safe to expose to frontend)"""
        return {
            'id': self.id,
            'name': self.name,
            'profile_picture': self.profile_picture,
            'is_premium': self.is_premium
        }

    def to_dict_profile(self):
        """Full profile info"""
        return {
            'id': self.id,
            'email': self.email,
            'name': self.name,
            'profile_picture': self.profile_picture,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'is_premium': self.is_premium,
            'premium_since': self.premium_since.isoformat() if self.premium_since else None,
            'providers': [acc.provider for acc in self.auth_accounts]
        }


class UserAuthAccount(db.Model):
    __tablename__ = 'user_auth_accounts'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    provider = db.Column(db.String(50), nullable=False)  # 'google', 'test'
    provider_user_id = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_used_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('provider', 'provider_user_id', name='unique_provider_account'),
    )


class Purchase(db.Model):
    __tablename__ = 'purchases'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    ticker = db.Column(db.String(10), nullable=False)
    purchase_date = db.Column(db.Date, nullable=False)
    amount = db.Column(db.Float, nullable=False)
    shares_bought = db.Column(db.Float, nullable=False)
    price_at_purchase = db.Column(db.Float, nullable=False)
    original_amount = db.Column(db.Float, nullable=True)
    original_currency = db.Column(db.String(3), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    sale_assignments = db.relationship('PurchaseSaleAssignment', backref='purchase',
                                      lazy=True, cascade='all, delete-orphan')

    @property
    def shares_sold(self):
        """Calculate total shares sold from this purchase."""
        return sum(assignment.shares_assigned for assignment in self.sale_assignments)

    @property
    def shares_remaining(self):
        """Calculate shares remaining after sales."""
        return self.shares_bought - self.shares_sold

    def to_dict(self):
        return {
            'id': self.id,
            'ticker': self.ticker,
            'purchase_date': self.purchase_date.isoformat(),
            'amount': self.amount,
            'shares_bought': self.shares_bought,
            'price_at_purchase': self.price_at_purchase,
            'original_amount': self.original_amount,
            'original_currency': self.original_currency,
            'created_at': self.created_at.isoformat(),
            'shares_remaining': self.shares_remaining
        }


class Sale(db.Model):
    __tablename__ = 'sales'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    ticker = db.Column(db.String(10), nullable=False)
    sale_date = db.Column(db.Date, nullable=False)
    shares_sold = db.Column(db.Float, nullable=False)
    price_at_sale = db.Column(db.Float, nullable=False)
    total_proceeds = db.Column(db.Float, nullable=False)

    # Reinvestment tracking
    reinvestment_purchase_id = db.Column(db.Integer, db.ForeignKey('purchases.id'), nullable=True)
    reinvested_amount = db.Column(db.Float, nullable=True)
    cash_retained = db.Column(db.Float, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    purchase_assignments = db.relationship('PurchaseSaleAssignment', backref='sale',
                                          lazy=True, cascade='all, delete-orphan')
    reinvestment_purchase = db.relationship('Purchase', foreign_keys=[reinvestment_purchase_id],
                                           backref='reinvested_from_sale')

    def to_dict(self):
        return {
            'id': self.id,
            'ticker': self.ticker,
            'sale_date': self.sale_date.isoformat(),
            'shares_sold': self.shares_sold,
            'price_at_sale': self.price_at_sale,
            'total_proceeds': self.total_proceeds,
            'reinvestment_purchase_id': self.reinvestment_purchase_id,
            'reinvested_amount': self.reinvested_amount,
            'cash_retained': self.cash_retained,
            'created_at': self.created_at.isoformat()
        }


class PurchaseSaleAssignment(db.Model):
    __tablename__ = 'purchase_sale_assignments'

    id = db.Column(db.Integer, primary_key=True)
    purchase_id = db.Column(db.Integer, db.ForeignKey('purchases.id'), nullable=False)
    sale_id = db.Column(db.Integer, db.ForeignKey('sales.id'), nullable=False)
    shares_assigned = db.Column(db.Float, nullable=False)
    cost_basis = db.Column(db.Float, nullable=False)
    proceeds = db.Column(db.Float, nullable=False)
    realized_gain_loss = db.Column(db.Float, nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'purchase_id': self.purchase_id,
            'sale_id': self.sale_id,
            'shares_assigned': self.shares_assigned,
            'cost_basis': self.cost_basis,
            'proceeds': self.proceeds,
            'realized_gain_loss': self.realized_gain_loss
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
        Index('ix_price_cache_ticker_date', 'ticker', 'date'),
    )


class PortfolioShare(db.Model):
    __tablename__ = 'portfolio_shares'

    id = db.Column(db.Integer, primary_key=True)
    share_token = db.Column(db.String(36), unique=True, nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # Snapshot data (percentages only - no dollar amounts for privacy)
    portfolio_return_pct = db.Column(db.Float, nullable=False)
    best_benchmark_ticker = db.Column(db.String(10), nullable=False)
    best_benchmark_name = db.Column(db.String(100), nullable=False)
    best_benchmark_return_pct = db.Column(db.Float, nullable=False)
    worst_benchmark_ticker = db.Column(db.String(10), nullable=False)
    worst_benchmark_name = db.Column(db.String(100), nullable=False)
    worst_benchmark_return_pct = db.Column(db.Float, nullable=False)
    opportunity_cost_pct = db.Column(db.Float, nullable=False)  # Difference vs best benchmark
    spy_return_pct = db.Column(db.Float, nullable=True)

    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    view_count = db.Column(db.Integer, default=0)

    # Relationships
    user = db.relationship('User', backref=db.backref('shares', lazy=True))

    def to_dict(self):
        return {
            'share_token': self.share_token,
            'portfolio_return_pct': self.portfolio_return_pct,
            'best_benchmark_ticker': self.best_benchmark_ticker,
            'best_benchmark_name': self.best_benchmark_name,
            'best_benchmark_return_pct': self.best_benchmark_return_pct,
            'worst_benchmark_ticker': self.worst_benchmark_ticker,
            'worst_benchmark_name': self.worst_benchmark_name,
            'worst_benchmark_return_pct': self.worst_benchmark_return_pct,
            'opportunity_cost_pct': self.opportunity_cost_pct,
            'spy_return_pct': self.spy_return_pct,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'view_count': self.view_count
        }


class PdfUploadLog(db.Model):
    """Tracks PDF upload attempts per user for daily rate limiting."""
    __tablename__ = 'pdf_upload_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    uploaded_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    file_size_bytes = db.Column(db.Integer, nullable=True)
    success = db.Column(db.Boolean, nullable=True)

    # Relationships
    user = db.relationship('User', backref=db.backref('pdf_uploads', lazy=True))

    # Index for efficient daily count queries
    __table_args__ = (
        db.Index('ix_pdf_upload_logs_user_date', 'user_id', 'uploaded_at'),
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
