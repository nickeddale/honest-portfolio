# Honest Portfolio - Complete Setup Guide

## Project Overview

Honest Portfolio is a Progressive Web App (PWA) that helps you track the opportunity cost of your stock portfolio by comparing your actual investments against benchmark stocks like SPY, AAPL, META, GOOGL, NVDA, and AMZN.

## File Structure

```
honest-portfolio/
├── app/
│   ├── __init__.py           # Flask app factory
│   ├── config.py             # Configuration
│   ├── models.py             # Database models
│   ├── routes/               # API endpoints
│   │   ├── purchases.py      # Purchase CRUD
│   │   ├── portfolio.py      # Portfolio analytics
│   │   └── stocks.py         # Stock data
│   ├── services/             # Business logic
│   │   └── portfolio.py      # Portfolio calculations
│   └── static/               # Frontend files
│       ├── index.html        # Main SPA
│       ├── manifest.json     # PWA manifest
│       ├── js/
│       │   ├── app.js       # Application logic
│       │   └── sw.js        # Service worker
│       └── icons/           # PWA icons
├── run.py                    # Application entry point
├── requirements.txt          # Python dependencies
└── .env.example             # Environment variables template

```

## Prerequisites

- Python 3.8+
- pip
- Modern web browser (Chrome, Firefox, Safari, or Edge)

## Installation Steps

### 1. Clone/Setup Project
```bash
cd /Users/nickdale/code/honest-portfolio
```

### 2. Create Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
```bash
cp .env.example .env
# Edit .env and add your configuration
```

Required environment variables:
- `SECRET_KEY` - Flask secret key
- `DATABASE_URL` - Database connection string (default: SQLite)

### 5. Create PWA Icons

The app includes a helper to generate icons:

**Option A: Use the HTML Generator**
1. Open `app/static/icons/generate-icons.html` in a browser
2. Right-click each canvas
3. Save as `icon-192.png` and `icon-512.png`
4. Place in `app/static/icons/` directory

**Option B: Use Online Tools**
- Visit https://www.favicon-generator.org/
- Upload a logo or create one
- Download 192x192 and 512x512 sizes

**Option C: Use Design Software**
- Create 192x192 and 512x512 PNG files
- Use the blue theme color: #1e40af
- Add "HP" text or a portfolio icon

### 6. Run the Application
```bash
python run.py
```

The app will be available at `http://localhost:5000`

## Testing the Application

### 1. Access the Frontend
Open your browser to `http://localhost:5000`

### 2. Add a Purchase
- Enter a stock ticker (e.g., TSLA)
- Select a purchase date
- Enter amount (e.g., 1000.00)
- Click "Add Purchase"

### 3. View Analytics
- Check the summary cards for total invested, current value, and opportunity cost
- Review the chart for historical performance comparison
- Examine the comparison table to see how your portfolio ranks

### 4. Test PWA Features
- Open DevTools → Application → Service Workers
- Verify the service worker is registered
- Try the app offline (stop the Flask server)
- Static assets should still load from cache

## API Endpoints

All endpoints are prefixed with `/api`:

### Purchases
- `GET /api/purchases` - List all purchases
- `POST /api/purchases` - Create new purchase
  ```json
  {
    "ticker": "TSLA",
    "purchase_date": "2024-01-01",
    "amount": 1000.00
  }
  ```
- `DELETE /api/purchases/:id` - Delete purchase

### Portfolio
- `GET /api/portfolio/summary` - Get portfolio summary
  ```json
  {
    "actual": {
      "total_invested": 1000.00,
      "current_value": 1150.00,
      "gain_loss": 150.00,
      "return_pct": 15.0
    },
    "alternatives": [...]
  }
  ```
- `GET /api/portfolio/history` - Get historical performance
  ```json
  {
    "dates": ["2024-01-01", "2024-01-02", ...],
    "actual": [1000.00, 1050.00, ...],
    "alternatives": {
      "SPY": [1000.00, 1020.00, ...],
      "AAPL": [1000.00, 1080.00, ...]
    }
  }
  ```

### Stocks
- `GET /api/stocks` - List comparison stocks
- `GET /api/stocks/:ticker/history` - Get stock price history

## Frontend Features

### Responsive Design
- Mobile-first approach
- Tailwind CSS utility classes
- Grid and flexbox layouts
- Responsive breakpoints (md, lg)

### Real-time Updates
- Form validation
- Error/success messages
- Loading states
- Optimistic UI updates

### Data Visualization
- Chart.js line chart
- Multiple datasets (portfolio + alternatives)
- Interactive tooltips
- Responsive chart sizing

### Progressive Web App
- Service worker for offline support
- Installable on mobile devices
- App manifest with icons
- Standalone display mode

## Development

### File Organization

**Frontend (app/static/)**
- `index.html` - HTML structure, no templating needed
- `js/app.js` - All JavaScript logic (353 lines)
- `js/sw.js` - Service worker for caching (53 lines)
- `manifest.json` - PWA configuration

**Backend (app/)**
- Models: Database schema with SQLAlchemy
- Routes: Flask blueprints for API endpoints
- Services: Business logic for calculations
- Config: Environment-based configuration

### Adding New Features

**Frontend:**
1. Add UI in `index.html`
2. Add logic in `js/app.js`
3. Update service worker cache if needed

**Backend:**
1. Update models in `models.py` if needed
2. Add route in appropriate blueprint
3. Add business logic in `services/`

## Troubleshooting

### Service Worker Not Registering
- Check browser console for errors
- Ensure HTTPS or localhost
- Clear browser cache and reload

### API Calls Failing
- Verify Flask server is running
- Check CORS settings in `__init__.py`
- Inspect network tab in DevTools

### Icons Not Showing
- Ensure icons exist in `static/icons/`
- Check manifest.json paths
- Clear browser cache

### Chart Not Rendering
- Verify Chart.js CDN is accessible
- Check console for Chart.js errors
- Ensure portfolioHistory has data

## Production Deployment

### Environment Variables
```bash
SECRET_KEY=your-secure-secret-key
DATABASE_URL=postgresql://user:pass@host/db
FLASK_ENV=production
```

### Static Files
- Consider using a CDN for Chart.js and Tailwind
- Enable gzip compression
- Set cache headers for static assets

### Database
- Use PostgreSQL or MySQL in production
- Run migrations for schema updates
- Regular backups recommended

### HTTPS
- Required for Service Worker to work
- Use Let's Encrypt for free SSL
- Configure reverse proxy (nginx/Apache)

## Browser Support

### Desktop
- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

### Mobile
- iOS Safari 14+
- Chrome Android 90+
- Samsung Internet 14+

## Performance

### Metrics
- First Contentful Paint: < 1s
- Time to Interactive: < 2s
- Lighthouse PWA Score: 90+

### Optimizations
- CDN for external libraries
- Service Worker caching
- Minimal JavaScript (no frameworks)
- Efficient DOM updates

## Security

### Frontend
- Input validation
- XSS prevention (textContent vs innerHTML)
- CORS configuration

### Backend
- SQL injection prevention (SQLAlchemy ORM)
- CSRF protection
- Environment variable secrets

## License

MIT License - See LICENSE file for details

## Support

For issues or questions:
1. Check the troubleshooting section
2. Review browser console for errors
3. Verify API endpoints are responding
4. Check Flask logs for backend errors
