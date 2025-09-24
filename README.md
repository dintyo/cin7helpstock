# Stock Forecasting Flask Application

A Python Flask application for stock forecasting and reorder point calculation using Cin7 Core (DEAR) API integration.

## Features

- **Cin7 API Integration**: Fetch orders, products, and stock levels from Cin7 Core
- **Sales Velocity Calculation**: Calculate daily/weekly/monthly sales velocity for SKUs
- **Stock Level Tracking**: Monitor stock on hand across VIC/QLD/NSW warehouses
- **Reorder Point Calculation**: Automatic calculation with configurable lead time and buffer stock
- **Forecast Generation**: Linear forecasting with stockout predictions
- **Trend Analysis**: Identify sales trends and seasonality patterns

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables

The `.env` file is already configured with your Cin7 credentials:
- `CIN7_API_KEY`: Your Cin7 Core API key
- `CIN7_ACCOUNT_ID`: Your Cin7 account ID
- `DATABASE_URL`: Database connection (defaults to SQLite for MVP)

### 3. Run the Application

```bash
python app.py
```

The application will start on `http://localhost:5000`

## API Endpoints

### Data Synchronization

#### Sync Orders from Cin7
```
POST /api/sync/orders
```
Fetches last 30 days of orders from Cin7 and stores them in the database.

#### Sync Products/SKUs
```
POST /api/sync/products
```
Fetches all products from Cin7 with dimensions and CBM calculations.

### Stock Management

#### Get Stock on Hand
```
GET /api/stock/on-hand
```
Returns current stock levels grouped by warehouse (VIC/QLD/NSW).

### Sales Analytics

#### Calculate Sales Velocity
```
GET /api/sales/velocity/<sku>
```
Returns sales velocity metrics for a specific SKU:
- Daily/weekly/monthly averages
- Trend analysis
- Variability metrics

### Forecasting

#### Calculate Reorder Points
```
POST /api/reorder/calculate
Body: {
    "lead_time_days": 30,
    "buffer_months": 1
}
```
Calculates reorder points for all SKUs based on:
- Current stock levels
- Sales velocity
- Lead time
- Safety stock buffer

Response includes:
- SKUs that need reordering
- Recommended order quantities
- Reorder points
- Safety stock levels

#### Generate SKU Forecast
```
GET /api/forecast/<sku>?days=90
```
Generates a forecast for the next N days showing:
- Projected stock levels
- Stockout risk dates
- Daily consumption predictions

## Quick Start Guide

### Step 1: Initial Data Sync

First, sync your data from Cin7:

```bash
# Sync products first
curl -X POST http://localhost:5000/api/sync/products

# Then sync recent orders (last 30 days)
curl -X POST http://localhost:5000/api/sync/orders
```

### Step 2: Check Stock Levels

```bash
curl http://localhost:5000/api/stock/on-hand
```

### Step 3: Calculate Reorder Points

```bash
curl -X POST http://localhost:5000/api/reorder/calculate \
  -H "Content-Type: application/json" \
  -d '{"lead_time_days": 30, "buffer_months": 1}'
```

### Step 4: View Sales Velocity for a SKU

```bash
curl http://localhost:5000/api/sales/velocity/YOUR_SKU_CODE
```

### Step 5: Generate Forecast

```bash
curl http://localhost:5000/api/forecast/YOUR_SKU_CODE?days=90
```

## Database Schema

The application uses SQLAlchemy with the following main tables:

- **products**: SKU master data with dimensions
- **orders**: Sales orders from Cin7
- **order_lines**: Individual line items in orders
- **stock_levels**: Current stock by SKU and warehouse
- **forecast_config**: Per-SKU forecasting parameters

## Key Calculations

### Sales Velocity
```
Daily Velocity = Total Units Sold / Number of Days
```

### Reorder Point
```
Reorder Point = (Lead Time × Daily Velocity) + Safety Stock
Safety Stock = Daily Velocity × (Buffer Months × 30)
```

### Recommended Order Quantity
```
Recommended Qty = Max(0, Reorder Point - Current Stock)
```

## Next Steps for Production

1. **Database**: Switch from SQLite to PostgreSQL for production
2. **Authentication**: Add API authentication/authorization
3. **Scheduling**: Add automated daily sync with Cin7
4. **UI**: Build a web interface for easier interaction
5. **Advanced Forecasting**: Implement more sophisticated forecasting models (ARIMA, etc.)
6. **Alerts**: Add email/SMS alerts for low stock conditions
7. **Reporting**: Generate PDF/Excel reports for purchasing decisions

## Troubleshooting

### API Rate Limits
The Cin7 client includes automatic retry logic with exponential backoff for rate limiting.

### Database Issues
If you encounter database errors, you can reset the database:
```bash
rm stock_forecast.db  # Remove SQLite database
python app.py  # Restart to recreate tables
```

### Cin7 Connection Issues
Check your credentials in `.env` and ensure your Cin7 account has API access enabled.

## License

MIT
