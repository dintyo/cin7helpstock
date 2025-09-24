"""
Stock Forecasting Flask Application
Main entry point for the application
"""
import os
from flask import Flask, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from datetime import datetime, timedelta

# Import our modules
from cin7_client import Cin7Client
from database import db, init_db
from stock_calculator import StockCalculator
from sales_velocity import SalesVelocityCalculator

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')
CORS(app)

# Initialize database
init_db(app)

# Initialize Cin7 client
cin7_client = Cin7Client(
    account_id=os.environ.get('CIN7_ACCOUNT_ID'),
    api_key=os.environ.get('CIN7_API_KEY'),
    base_url=os.environ.get('CIN7_BASE_URL')
)

# Initialize calculators
stock_calculator = StockCalculator(db)
velocity_calculator = SalesVelocityCalculator(db)


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat()
    })


@app.route('/api/sync/orders', methods=['POST'])
def sync_orders():
    """Sync orders from Cin7 API"""
    try:
        # Get date range for sync (last 30 days by default)
        from_date = (datetime.utcnow() - timedelta(days=30)).strftime('%Y-%m-%d')
        to_date = datetime.utcnow().strftime('%Y-%m-%d')
        
        # Fetch orders from Cin7
        orders = cin7_client.fetch_orders(
            order_date_from=from_date,
            order_date_to=to_date
        )
        
        # Store orders in database
        stored_count = 0
        for order in orders:
            if stock_calculator.store_order(order):
                stored_count += 1
        
        return jsonify({
            'success': True,
            'message': f'Synced {stored_count} orders',
            'total_fetched': len(orders),
            'date_range': {'from': from_date, 'to': to_date}
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/sync/products', methods=['POST'])
def sync_products():
    """Sync products/SKUs from Cin7 API"""
    try:
        # Fetch products from Cin7
        products = cin7_client.fetch_products()
        
        # Store products in database
        stored_count = 0
        for product in products:
            if stock_calculator.store_product(product):
                stored_count += 1
        
        return jsonify({
            'success': True,
            'message': f'Synced {stored_count} products',
            'total_fetched': len(products)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/stock/on-hand', methods=['GET'])
def get_stock_on_hand():
    """Get current stock on hand by warehouse"""
    try:
        # Fetch current stock levels from Cin7
        stock_data = cin7_client.fetch_stock_on_hand()
        
        # Group by warehouse
        warehouse_stock = stock_calculator.calculate_stock_by_warehouse(stock_data)
        
        return jsonify({
            'success': True,
            'data': warehouse_stock,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/sales/velocity/<sku>', methods=['GET'])
def get_sales_velocity(sku):
    """Calculate sales velocity for a specific SKU"""
    try:
        # Calculate velocity (units per day) over last 30 days
        velocity_data = velocity_calculator.calculate_velocity(
            sku=sku,
            days=30
        )
        
        return jsonify({
            'success': True,
            'sku': sku,
            'data': velocity_data
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/reorder/calculate', methods=['POST'])
def calculate_reorder_points():
    """Calculate reorder points for all SKUs"""
    from flask import request
    
    try:
        # Get parameters
        data = request.get_json() or {}
        lead_time_days = data.get('lead_time_days', 30)  # Default 30 days
        buffer_months = data.get('buffer_months', 1)  # Default 1 month buffer
        
        # Get all SKUs
        skus = stock_calculator.get_all_skus()
        
        reorder_data = []
        for sku in skus:
            # Get current stock
            stock_on_hand = stock_calculator.get_stock_on_hand(sku['sku'])
            
            # Calculate sales velocity
            velocity = velocity_calculator.calculate_velocity(sku['sku'], days=30)
            
            # Calculate reorder point
            # Reorder Point = (Lead Time × Average Daily Sales) + Safety Stock
            daily_velocity = velocity.get('daily_average', 0)
            safety_stock = daily_velocity * (buffer_months * 30)  # Convert months to days
            reorder_point = (lead_time_days * daily_velocity) + safety_stock
            
            # Calculate recommended order quantity (simple EOQ approximation)
            # For MVP, we'll use a simple formula: order for lead_time + buffer period
            recommended_qty = max(0, reorder_point - stock_on_hand.get('total', 0))
            
            reorder_data.append({
                'sku': sku['sku'],
                'description': sku.get('description', ''),
                'stock_on_hand': stock_on_hand,
                'daily_velocity': round(daily_velocity, 2),
                'reorder_point': round(reorder_point, 0),
                'safety_stock': round(safety_stock, 0),
                'recommended_order_qty': round(recommended_qty, 0),
                'needs_reorder': stock_on_hand.get('total', 0) <= reorder_point
            })
        
        # Sort by urgency (needs_reorder first, then by recommended_qty)
        reorder_data.sort(key=lambda x: (not x['needs_reorder'], -x['recommended_order_qty']))
        
        return jsonify({
            'success': True,
            'parameters': {
                'lead_time_days': lead_time_days,
                'buffer_months': buffer_months
            },
            'data': reorder_data,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/forecast/<sku>', methods=['GET'])
def forecast_sku(sku):
    """Generate forecast for a specific SKU"""
    from flask import request
    
    try:
        # Get parameters
        days_ahead = int(request.args.get('days', 90))  # Default 90 days forecast
        
        # Get historical data
        velocity = velocity_calculator.calculate_velocity(sku, days=90)
        stock = stock_calculator.get_stock_on_hand(sku)
        
        # Simple linear forecast
        daily_velocity = velocity.get('daily_average', 0)
        
        forecast = []
        current_stock = stock.get('total', 0)
        
        for day in range(1, days_ahead + 1):
            projected_stock = current_stock - (daily_velocity * day)
            forecast.append({
                'day': day,
                'date': (datetime.utcnow() + timedelta(days=day)).strftime('%Y-%m-%d'),
                'projected_stock': max(0, projected_stock),
                'stockout_risk': projected_stock <= 0
            })
        
        # Find stockout date
        stockout_day = next((f['day'] for f in forecast if f['stockout_risk']), None)
        
        return jsonify({
            'success': True,
            'sku': sku,
            'current_stock': current_stock,
            'daily_velocity': round(daily_velocity, 2),
            'stockout_in_days': stockout_day,
            'forecast': forecast
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5000)
