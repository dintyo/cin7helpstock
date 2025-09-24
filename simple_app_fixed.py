"""
Simple Stock Forecasting MVP - Fixed version with better error handling
"""
import os
from flask import Flask, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv
from datetime import datetime, timedelta
import sqlite3
import requests
import json
import logging
import time

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

# Database setup
DATABASE = 'stock_forecast.db'

def init_db():
    """Initialize SQLite database with simple schema"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # Simple tables for MVP
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY,
            sku TEXT UNIQUE NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY,
            sku TEXT NOT NULL,
            quantity REAL NOT NULL,
            sale_date DATE NOT NULL,
            warehouse TEXT,
            order_number TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS current_stock (
            id INTEGER PRIMARY KEY,
            sku TEXT NOT NULL,
            warehouse TEXT NOT NULL,
            quantity REAL NOT NULL,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(sku, warehouse)
        )
    ''')
    
    conn.commit()
    conn.close()

def get_db():
    """Get database connection"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row  # Return rows as dictionaries
    return conn

class SimpleCin7Client:
    """Simplified Cin7 client with better error handling"""
    
    def __init__(self):
        self.account_id = os.environ.get('CIN7_ACCOUNT_ID')
        self.api_key = os.environ.get('CIN7_API_KEY')
        self.base_url = os.environ.get('CIN7_BASE_URL', 'https://inventory.dearsystems.com/ExternalApi/v2')
        
        if not self.account_id or not self.api_key:
            raise ValueError("Missing CIN7_ACCOUNT_ID or CIN7_API_KEY in environment")
        
        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 1.0  # Minimum 1 second between requests
    
    def _wait_for_rate_limit(self):
        """Ensure we don't exceed rate limits"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_request_interval:
            sleep_time = self.min_request_interval - elapsed
            logger.info(f"Rate limiting: waiting {sleep_time:.1f}s")
            time.sleep(sleep_time)
    
    def _make_request(self, endpoint, params=None, timeout=15):
        """Make API request to Cin7 with proper rate limiting"""
        self._wait_for_rate_limit()
        
        headers = {
            'api-auth-accountid': self.account_id,
            'api-auth-applicationkey': self.api_key,
            'Content-Type': 'application/json'
        }
        
        url = f"{self.base_url}{endpoint}"
        
        try:
            logger.info(f"Making request to: {endpoint}")
            response = requests.get(url, headers=headers, params=params, timeout=timeout)
            self.last_request_time = time.time()
            
            if response.status_code == 429:
                logger.warning("Rate limited - waiting 60 seconds...")
                time.sleep(60)
                return self._make_request(endpoint, params, timeout)
            
            if response.status_code == 503:
                logger.warning("Service unavailable - waiting 10 seconds...")
                time.sleep(10)
                return self._make_request(endpoint, params, timeout)
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.Timeout:
            logger.error(f"Timeout after {timeout}s for {endpoint}")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed for {endpoint}: {e}")
            raise
    
    def test_connection(self):
        """Test API connection"""
        try:
            result = self._make_request('/SaleList', {'Page': 1, 'Limit': 1})
            return True, f"Connected! Found {len(result.get('SaleList', []))} orders on first page"
        except Exception as e:
            return False, str(e)
    
    def fetch_recent_orders(self, days=30, max_orders=5):
        """Fetch recent orders with limit for testing"""
        from_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        
        try:
            orders = []
            page = 1
            
            logger.info(f"Fetching orders from {from_date}, max {max_orders} orders")
            
            while page <= 2 and len(orders) < max_orders:  # Limit pages for testing
                params = {
                    'Page': page,
                    'Limit': min(100, max_orders),
                    'OrderDateFrom': from_date
                }
                
                logger.info(f"Fetching page {page}...")
                result = self._make_request('/SaleList', params)
                sale_list = result.get('SaleList', [])
                
                if not sale_list:
                    break
                
                # Filter valid orders and extract basic data
                for sale in sale_list:
                    if sale.get('Status') != 'VOIDED' and len(orders) < max_orders:
                        orders.append({
                            'sale_id': sale.get('SaleID'),
                            'order_number': sale.get('OrderNumber'),
                            'order_date': sale.get('OrderDate', '').split('T')[0],
                            'warehouse': self._map_location(sale.get('OrderLocationID'))
                        })
                
                if len(sale_list) < 100:
                    break
                
                page += 1
            
            logger.info(f"Found {len(orders)} valid orders")
            return orders
            
        except Exception as e:
            logger.error(f"Failed to fetch orders: {e}")
            return []
    
    def fetch_order_lines(self, sale_id):
        """Fetch detailed order lines for a sale with timeout protection"""
        try:
            logger.info(f"Fetching lines for order: {sale_id}")
            result = self._make_request('/Sale', {'ID': sale_id}, timeout=10)
            
            # Extract lines from order
            lines = []
            if 'Order' in result and 'Lines' in result['Order']:
                for line in result['Order']['Lines']:
                    lines.append({
                        'sku': line.get('SKU', ''),
                        'quantity': line.get('Quantity', 0),
                        'description': line.get('Name', '')
                    })
            
            logger.info(f"Found {len(lines)} lines for order {sale_id}")
            return lines
            
        except Exception as e:
            logger.error(f"Failed to fetch order lines for {sale_id}: {e}")
            return []
    
    def _map_location(self, location_id):
        """Simple location mapping - enhance later"""
        # For MVP, return a default
        return 'NSW'  # Can be enhanced with actual location lookup

# Initialize
init_db()
cin7 = SimpleCin7Client()

@app.route('/health')
def health():
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

@app.route('/test-cin7')
def test_cin7():
    """Test Cin7 API connection"""
    success, message = cin7.test_connection()
    return jsonify({
        'success': success,
        'message': message,
        'account_id': cin7.account_id[:8] + '...' if cin7.account_id else None
    })

@app.route('/sync-sales')
def sync_sales():
    """Sync recent sales data for velocity calculation - LIMITED FOR TESTING"""
    try:
        logger.info("Starting sales sync...")
        
        # Fetch recent orders (LIMIT TO 3 FOR TESTING)
        orders = cin7.fetch_recent_orders(days=30, max_orders=3)
        
        if not orders:
            return jsonify({
                'success': True,
                'message': 'No orders found to sync',
                'orders_processed': 0
            })
        
        conn = get_db()
        cursor = conn.cursor()
        
        total_lines = 0
        processed_orders = 0
        
        # For each order, get the detailed lines
        for i, order in enumerate(orders):
            logger.info(f"Processing order {i+1}/{len(orders)}: {order['order_number']}")
            
            try:
                lines = cin7.fetch_order_lines(order['sale_id'])
                
                for line in lines:
                    if line['sku'] and line['quantity'] > 0:
                        # Store product if not exists
                        cursor.execute('''
                            INSERT OR IGNORE INTO products (sku, description)
                            VALUES (?, ?)
                        ''', (line['sku'], line['description']))
                        
                        # Store sale
                        cursor.execute('''
                            INSERT INTO sales (sku, quantity, sale_date, warehouse, order_number)
                            VALUES (?, ?, ?, ?, ?)
                        ''', (
                            line['sku'],
                            line['quantity'],
                            order['order_date'],
                            order['warehouse'],
                            order['order_number']
                        ))
                        
                        total_lines += 1
                
                conn.commit()
                processed_orders += 1
                
                # Progress feedback
                logger.info(f"Processed order {order['order_number']}: {len(lines)} lines")
                
            except Exception as e:
                logger.error(f"Failed to process order {order['order_number']}: {e}")
                continue
        
        conn.close()
        
        return jsonify({
            'success': True,
            'orders_found': len(orders),
            'orders_processed': processed_orders,
            'lines_stored': total_lines,
            'message': f'Sales data synced successfully (limited to {len(orders)} orders for testing)'
        })
        
    except Exception as e:
        logger.error(f"Sync failed: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/velocity/<sku>')
def calculate_velocity(sku):
    """Calculate sales velocity for a SKU"""
    try:
        days = int(request.args.get('days', 30))
        
        conn = get_db()
        cursor = conn.cursor()
        
        # Get sales data for the SKU
        cursor.execute('''
            SELECT 
                SUM(quantity) as total_quantity,
                COUNT(*) as sale_count,
                MIN(sale_date) as first_sale,
                MAX(sale_date) as last_sale
            FROM sales 
            WHERE sku = ? 
            AND sale_date >= date('now', '-{} days')
        '''.format(days), (sku,))
        
        result = cursor.fetchone()
        
        if not result or not result['total_quantity']:
            return jsonify({
                'sku': sku,
                'daily_velocity': 0,
                'weekly_velocity': 0,
                'monthly_velocity': 0,
                'message': 'No sales data found'
            })
        
        total_qty = result['total_quantity']
        actual_days = days
        
        # Calculate velocity
        daily_velocity = total_qty / actual_days
        
        # Get product info
        cursor.execute('SELECT description FROM products WHERE sku = ?', (sku,))
        product = cursor.fetchone()
        
        conn.close()
        
        return jsonify({
            'sku': sku,
            'description': product['description'] if product else '',
            'period_days': days,
            'total_quantity_sold': total_qty,
            'daily_velocity': round(daily_velocity, 2),
            'weekly_velocity': round(daily_velocity * 7, 2),
            'monthly_velocity': round(daily_velocity * 30, 2),
            'first_sale': result['first_sale'],
            'last_sale': result['last_sale']
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/sync-sales-simple')
def sync_sales_simple():
    """Simplified sync that just gets order list without details"""
    try:
        logger.info("Starting simple sales sync (list only)...")
        
        # Just get the order list without fetching details
        from_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        
        params = {
            'Page': 1,
            'Limit': 10,
            'OrderDateFrom': from_date
        }
        
        result = cin7._make_request('/SaleList', params)
        orders = result.get('SaleList', [])
        
        # Filter valid orders
        valid_orders = [o for o in orders if o.get('Status') != 'VOIDED']
        
        return jsonify({
            'success': True,
            'total_found': len(orders),
            'valid_orders': len(valid_orders),
            'sample_orders': [
                {
                    'order_number': o.get('OrderNumber'),
                    'order_date': o.get('OrderDate', '').split('T')[0],
                    'status': o.get('Status')
                } for o in valid_orders[:3]
            ],
            'message': 'Simple sync completed (order list only)'
        })
        
    except Exception as e:
        logger.error(f"Simple sync failed: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/stock-status')
def stock_status():
    """Quick overview of stock status"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Get basic stats
        cursor.execute('SELECT COUNT(DISTINCT sku) FROM products')
        total_skus = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(DISTINCT sku) FROM sales WHERE sale_date >= date("now", "-30 days")')
        active_skus = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM sales WHERE sale_date >= date("now", "-7 days")')
        recent_sales = cursor.fetchone()[0]
        
        conn.close()
        
        return jsonify({
            'total_skus': total_skus,
            'active_skus_30d': active_skus,
            'sales_last_7d': recent_sales,
            'database_status': 'connected',
            'last_updated': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("🚀 Starting Stock Forecasting App...")
    print("📊 Database initializing...")
    init_db()
    print("✅ Database ready!")
    print("🌐 Starting Flask server on http://localhost:5000")
    print("\nAvailable endpoints:")
    print("  GET  /health - Health check")
    print("  GET  /test-cin7 - Test Cin7 connection")
    print("  GET  /sync-sales-simple - Quick sync (order list only)")
    print("  GET  /sync-sales - Full sync (with order details)")
    print("  GET  /stock-status - Database status")
    print("  GET  /velocity/<sku> - Calculate velocity for SKU")
    
    app.run(debug=True, port=5000)
