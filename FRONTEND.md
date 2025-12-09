# Honest Portfolio - Frontend Documentation

## Overview

The frontend is a Progressive Web App (PWA) built with Vanilla JavaScript, Tailwind CSS, and Chart.js. It provides a responsive, mobile-friendly interface for tracking stock portfolio performance and opportunity costs.

## Tech Stack

- **Vanilla JavaScript (ES6+)** - No framework dependencies
- **Tailwind CSS** (CDN) - Utility-first CSS framework
- **Chart.js** (CDN) - Interactive charts for portfolio visualization
- **Service Worker** - Offline support and PWA capabilities

## File Structure

```
app/static/
├── index.html              # Main SPA shell
├── manifest.json           # PWA manifest
├── js/
│   ├── app.js             # Main application logic
│   └── sw.js              # Service worker for offline support
└── icons/
    ├── README.md          # Icon creation instructions
    ├── generate-icons.html # Helper to generate icons
    └── icon.svg           # SVG template
```

## Features

### 1. Add Stock Purchase Form
- Input stock ticker, purchase date, and amount
- Client-side validation
- Real-time feedback on submission
- Automatic uppercase conversion for tickers

### 2. Summary Cards
- **Total Invested**: Sum of all purchases
- **Your Portfolio Value**: Current value of actual holdings
- **Best Alternative**: Highest performing comparison stock
- **Opportunity Cost**: Difference between your portfolio and the best alternative

### 3. Interactive Chart
- Line chart comparing portfolio performance over time
- Your portfolio vs. comparison stocks (SPY, AAPL, META, etc.)
- Responsive design
- Formatted tooltips with currency values

### 4. Comparison Table
- Detailed breakdown of all investments
- Sortable by performance
- Highlights the best performer with a crown icon
- Color-coded gains/losses

### 5. Purchases List
- All user purchases with details
- Delete functionality
- Shows shares bought and purchase price

## Key Functions

### State Management
```javascript
let purchases = [];           // User's stock purchases
let portfolioSummary = null;  // Summary stats
let portfolioHistory = null;  // Historical performance data
let chart = null;             // Chart.js instance
```

### API Integration
- `loadPurchases()` - Fetches all user purchases
- `loadPortfolioSummary()` - Gets current portfolio summary
- `loadPortfolioHistory()` - Retrieves historical performance data
- `handlePurchaseSubmit()` - Creates new purchase
- `deletePurchase(id)` - Removes a purchase

### UI Rendering
- `renderPurchasesList()` - Displays user purchases
- `renderSummaryCards()` - Updates summary metrics
- `renderComparisonTable()` - Populates comparison table
- `renderChart()` - Creates/updates Chart.js visualization

### Utility Functions
- `formatCurrency(value)` - Formats numbers as USD
- `formatDate(dateStr)` - Formats dates for display
- `showError(message)` - Shows error messages
- `showSuccess(message)` - Shows success messages

## PWA Features

### Service Worker (sw.js)
- **Caching Strategy**: Network-first for API calls, cache-first for static assets
- **Offline Support**: Cached static assets available offline
- **Auto-update**: New service worker activates on reload

### Manifest (manifest.json)
- **Install Prompt**: Users can install as standalone app
- **Theme Color**: Blue (#1e40af)
- **Icons**: 192px and 512px for various devices
- **Display Mode**: Standalone (hides browser UI)

## API Endpoints Used

- `GET /api/purchases` - List all purchases
- `POST /api/purchases` - Create new purchase
- `DELETE /api/purchases/:id` - Delete purchase
- `GET /api/portfolio/summary` - Get portfolio summary
- `GET /api/portfolio/history` - Get historical performance

## Styling

### Tailwind CSS Classes Used
- **Layout**: Container, grid, flex
- **Spacing**: Padding (p-*), margin (m-*)
- **Colors**: Gray scale, blue (primary), green (positive), red (negative)
- **Typography**: Font weights, sizes, colors
- **Components**: Rounded corners, shadows, borders

### Custom Styling
```css
[x-cloak] { display: none !important; }
```
Used for hiding elements during initialization.

## Browser Support

- Modern browsers with ES6+ support
- Chrome/Edge 90+
- Firefox 88+
- Safari 14+
- Mobile browsers (iOS Safari, Chrome Android)

## Development

### Testing Locally
1. Start the Flask backend: `python run.py`
2. Open browser to `http://localhost:5000`
3. Check console for Service Worker registration
4. Test offline mode by stopping the server (static assets should still load)

### Debugging
- Open browser DevTools
- Check Console for errors
- Network tab to monitor API calls
- Application tab to inspect Service Worker and Cache Storage

## Creating PWA Icons

### Option 1: Use the Generator
1. Open `/static/icons/generate-icons.html` in a browser
2. Right-click each canvas and save as PNG
3. Save as `icon-192.png` and `icon-512.png`

### Option 2: Online Tools
- https://www.favicon-generator.org/
- https://realfavicongenerator.net/

### Option 3: Design Software
- Create 192x192 and 512x512 PNG files
- Use brand colors and logo
- Place in `/static/icons/` directory

## Performance Optimizations

1. **Lazy Loading**: Chart only renders when data is available
2. **Debouncing**: Form submissions disabled during API calls
3. **Caching**: Service Worker caches static assets
4. **CDN**: Tailwind and Chart.js loaded from CDN
5. **Minimal Dependencies**: No heavy frameworks

## Future Enhancements

- [ ] Dark mode toggle
- [ ] Export portfolio data as CSV
- [ ] Push notifications for stock alerts
- [ ] Offline data sync
- [ ] Chart customization options
- [ ] Multiple portfolio support
- [ ] Stock price alerts
