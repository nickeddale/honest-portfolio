from flask import Flask, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import os

db = SQLAlchemy()

def create_app():
    app = Flask(__name__, static_folder='static', template_folder='../templates')

    # Configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///portfolio.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Initialize extensions
    db.init_app(app)
    CORS(app)

    # Register blueprints
    from app.routes.purchases import purchases_bp
    from app.routes.portfolio import portfolio_bp
    from app.routes.stocks import stocks_bp

    app.register_blueprint(purchases_bp, url_prefix='/api')
    app.register_blueprint(portfolio_bp, url_prefix='/api')
    app.register_blueprint(stocks_bp, url_prefix='/api')

    # Serve the SPA
    @app.route('/')
    def index():
        return app.send_static_file('index.html')

    # Serve favicon
    @app.route('/favicon.ico')
    def favicon():
        return send_from_directory(app.static_folder, 'favicon.ico')

    # Create tables
    with app.app_context():
        db.create_all()
        from app.models import seed_comparison_stocks
        seed_comparison_stocks()

    # CLI commands
    @app.cli.command('seed-trades')
    def seed_trades_command():
        """Load Trade Republic test data."""
        from app.seeds.trade_republic_data import seed_trade_republic_data
        seed_trade_republic_data()
        print('Trade Republic data seeded successfully!')

    return app
