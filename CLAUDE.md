# Honest Portfolio

Flask-based Progressive Web App that tracks portfolio opportunity cost by comparing actual stock purchases against benchmark stocks (SPY, AAPL, META, GOOGL, NVDA, AMZN).

## Quick Start

```bash
# Setup
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run development server
python run.py  # http://localhost:5000

# Production
gunicorn app:create_app()
```

## Project Structure

```
app/
├── __init__.py          # App factory, blueprint registration
├── config.py            # Dev/prod configuration
├── models.py            # Purchase, ComparisonStock, PriceCache models
├── routes/              # API blueprints
│   ├── purchases.py     # Purchase CRUD
│   ├── portfolio.py     # Portfolio analytics
│   └── stocks.py        # Stock validation, comparison data
├── services/
│   └── stock_data.py    # yfinance integration, price caching
└── static/              # Frontend SPA
    ├── index.html       # Main page
    ├── js/app.js        # Frontend logic
    └── js/sw.js         # Service worker
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/purchases` | GET | List all purchases |
| `/api/purchases` | POST | Create purchase |
| `/api/purchases/<id>` | DELETE | Delete purchase |
| `/api/portfolio/summary` | GET | Portfolio stats vs alternatives |
| `/api/portfolio/history` | GET | Historical performance time series |
| `/api/stock/validate/<ticker>` | GET | Validate stock ticker |
| `/api/comparison-stocks` | GET | List benchmark stocks |

## Tech Stack

- **Backend**: Flask, Flask-SQLAlchemy, Flask-CORS, yfinance
- **Database**: SQLite (instance/portfolio.db)
- **Frontend**: Vanilla JS, Tailwind CSS (CDN), Chart.js (CDN)
- **PWA**: Service worker for offline support

## Development Notes

- No testing framework configured
- Stock prices cached in PriceCache model
- Frontend is a single-page app in `app/static/`
