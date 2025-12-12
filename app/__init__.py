from flask import Flask, send_from_directory, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
import os

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()


def create_app():
    app = Flask(__name__, static_folder='static', template_folder='../templates')

    # Load configuration
    from app.config import DevelopmentConfig, ProductionConfig
    if os.environ.get('FLASK_ENV') == 'production':
        app.config.from_object(ProductionConfig)
    else:
        app.config.from_object(DevelopmentConfig)

    # Initialize extensions
    db.init_app(app)
    CORS(app, supports_credentials=True)
    login_manager.init_app(app)
    csrf.init_app(app)

    # Initialize OAuth
    from app.auth import init_oauth
    init_oauth(app)

    # Configure login manager
    login_manager.login_view = None  # We handle redirects ourselves
    login_manager.session_protection = 'basic'

    @login_manager.user_loader
    def load_user(user_id):
        from app.models import User
        return User.query.get(int(user_id))

    @login_manager.unauthorized_handler
    def unauthorized():
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Unauthorized - please log in'}), 401
        return send_from_directory(app.static_folder, 'login.html')

    # Register blueprints
    from app.routes.purchases import purchases_bp
    from app.routes.portfolio import portfolio_bp
    from app.routes.stocks import stocks_bp
    from app.routes.auth import auth_bp
    from app.routes.test_auth import test_auth_bp
    from app.routes.share import share_bp
    from app.routes.guest import guest_bp

    app.register_blueprint(purchases_bp, url_prefix='/api')
    app.register_blueprint(portfolio_bp, url_prefix='/api')
    app.register_blueprint(stocks_bp, url_prefix='/api')
    app.register_blueprint(auth_bp, url_prefix='/api')
    app.register_blueprint(test_auth_bp, url_prefix='/api')
    app.register_blueprint(share_bp, url_prefix='/api')
    app.register_blueprint(guest_bp, url_prefix='/api')

    # Exempt certain routes from CSRF
    csrf.exempt(auth_bp)  # OAuth callbacks need to be exempt
    csrf.exempt(test_auth_bp)  # Test endpoints exempt for ease of testing
    csrf.exempt(share_bp)  # Public GET endpoints need to be exempt
    csrf.exempt(guest_bp)  # Guest endpoints are public (except migrate which uses session)

    # Serve the SPA
    @app.route('/')
    def index():
        return app.send_static_file('index.html')

    # Serve login page
    @app.route('/login.html')
    def login_page():
        return app.send_static_file('login.html')

    # Serve public share page
    @app.route('/share/<share_token>')
    def share_page(share_token):
        return app.send_static_file('share.html')

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
