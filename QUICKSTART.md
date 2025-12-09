# Honest Portfolio - Quick Start

## Get Running in 5 Minutes

### 1. Install Dependencies
```bash
cd /Users/nickdale/code/honest-portfolio
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Set Up Environment
```bash
cp .env.example .env
```

### 3. Start the Application
```bash
python run.py
```

### 4. Open in Browser
Navigate to: `http://localhost:5000`

### 5. Test It Out
1. Add a stock purchase (e.g., TSLA, date: 2024-01-01, amount: $1000)
2. View the comparison against benchmark stocks
3. Check the performance chart
4. See your opportunity cost

## What You Get

### Features
- Track multiple stock purchases
- Compare against 6 benchmark stocks (SPY, AAPL, META, GOOGL, NVDA, AMZN)
- Interactive performance chart
- Real-time opportunity cost calculation
- Progressive Web App (installable on mobile)
- Offline support via Service Worker

### Frontend Stack
- Vanilla JavaScript (no framework)
- Tailwind CSS (utility-first styling)
- Chart.js (interactive charts)
- Service Worker (offline support)

### Backend Stack
- Flask (Python web framework)
- SQLAlchemy (ORM)
- SQLite (development database)
- yfinance (stock data)

## File Locations

**Frontend:**
- `/app/static/index.html` - Main UI
- `/app/static/js/app.js` - Application logic
- `/app/static/js/sw.js` - Service worker
- `/app/static/manifest.json` - PWA manifest

**Backend:**
- `/app/__init__.py` - Flask app setup
- `/app/models.py` - Database models
- `/app/routes/` - API endpoints
- `/app/services/` - Business logic

## API Endpoints

**Base URL:** `http://localhost:5000/api`

- `GET /purchases` - List purchases
- `POST /purchases` - Add purchase
- `DELETE /purchases/:id` - Remove purchase
- `GET /portfolio/summary` - Portfolio stats
- `GET /portfolio/history` - Historical data
- `GET /stocks` - Comparison stocks

## Next Steps

1. **Generate Icons:**
   - Open `/static/icons/generate-icons.html` in browser
   - Save canvases as PNG files
   - Place in `/static/icons/` directory

2. **Customize:**
   - Add more comparison stocks in `models.py`
   - Modify chart colors in `app.js`
   - Update theme colors in Tailwind config

3. **Deploy:**
   - See `SETUP.md` for production deployment guide
   - Use PostgreSQL for production database
   - Enable HTTPS for PWA features

## Troubleshooting

**App won't start:**
- Check Python version (3.8+)
- Verify dependencies installed: `pip list`
- Check port 5000 isn't in use

**No data showing:**
- Check browser console for errors
- Verify API endpoints: `curl http://localhost:5000/api/purchases`
- Check Flask logs in terminal

**Service Worker issues:**
- Use Chrome DevTools → Application → Service Workers
- Unregister and reload
- Clear cache storage

## Development Tips

### Hot Reload
The Flask app runs in debug mode, so backend changes reload automatically.
Frontend changes require a browser refresh.

### Testing API
Use curl or Postman:
```bash
# Add purchase
curl -X POST http://localhost:5000/api/purchases \
  -H "Content-Type: application/json" \
  -d '{"ticker":"TSLA","purchase_date":"2024-01-01","amount":1000.00}'

# Get summary
curl http://localhost:5000/api/portfolio/summary
```

### Browser DevTools
- Console: JavaScript errors
- Network: API call monitoring
- Application: Service Worker, Cache, Storage
- Performance: Load times

## Project Structure

```
honest-portfolio/
├── app/
│   ├── static/          # Frontend (HTML, JS, CSS)
│   ├── routes/          # API endpoints
│   ├── services/        # Business logic
│   └── models.py        # Database models
├── run.py              # Start server
└── requirements.txt    # Dependencies
```

## Learn More

- `FRONTEND.md` - Detailed frontend documentation
- `SETUP.md` - Complete setup and deployment guide
- `README.md` - Project overview (if exists)

## Need Help?

1. Check the error message in browser console or terminal
2. Review the troubleshooting sections in this guide
3. Verify all dependencies are installed correctly
4. Check that the database file was created (portfolio.db)

---

**Happy tracking!** Your opportunity costs await.
