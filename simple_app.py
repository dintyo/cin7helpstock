"""
Simple Stock Forecasting MVP
Focus on core functionality first
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
    """Simplified Cin7 client for testing"""
    
    def __init__(self):
        self.account_id = os.environ.get('CIN7_ACCOUNT_ID')
        self.api_key = os.environ.get('CIN7_API_KEY')
        self.base_url = os.environ.get('CIN7_BASE_URL', 'https://inventory.dearsystems.com/ExternalApi/v2')
        
        if not self.account_id or not self.api_key:
            raise ValueError("Missing CIN7_ACCOUNT_ID or CIN7_API_KEY in environment")
    
    def _make_request(self, endpoint, params=None):
        """Make API request to Cin7"""
        headers = {
            'api-auth-accountid': self.account_id,
            'api-auth-applicationkey': self.api_key,
            'Content-Type': 'application/json'
        }
        
        url = f"{self.base_url}{endpoint}"
        response = requests.get(url, headers=headers, params=params, timeout=30)
        
        if response.status_code == 429:
            logger.warning("Rate limited - waiting...")
            import time
            time.sleep(5)
            return self._make_request(endpoint, params)
        
        response.raise_for_status()
        return response.json()
    
    def test_connection(self):
        """Test API connection"""
        try:
            result = self._make_request('/SaleList', {'Page': 1, 'Limit': 1})
            return True, f"Connected! Found {len(result.get('SaleList', []))} orders on first page"
        except Exception as e:
            return False, str(e)
    
    def fetch_recent_orders(self, days=30):
        """Fetch recent orders for velocity calculation"""
        from_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        
        try:
            orders = []
            page = 1
            
            while page <= 5:  # Limit to 5 pages for MVP
                params = {
                    'Page': page,
                    'Limit': 100,
                    'OrderDateFrom': from_date
                }
                
                result = self._make_request('/SaleList', params)
                sale_list = result.get('SaleList', [])
                
                if not sale_list:
                    break
                
                # Filter valid orders and extract basic data
                for sale in sale_list:
                    if sale.get('Status') != 'VOIDED':  # Skip cancelled
                        orders.append({
                            'sale_id': sale.get('SaleID'),
                            'order_number': sale.get('OrderNumber'),
                            'order_date': sale.get('OrderDate', '').split('T')[0],
                            'warehouse': self._map_location(sale.get('OrderLocationID'))
                        })
                
                if len(sale_list) < 100:
                    break
                
                page += 1
                import time
                time.sleep(1)  # Rate limiting
            
            return orders
            
        except Exception as e:
            logger.error(f"Failed to fetch orders: {e}")
            return []
    
    def fetch_order_lines(self, sale_id):
        """Fetch detailed order lines for a sale"""
        try:
            result = self._make_request('/Sale', {'ID': sale_id})
            
            # Extract lines from order
            lines = []
            if 'Order' in result and 'Lines' in result['Order']:
                for line in result['Order']['Lines']:
                    lines.append({
                        'sku': line.get('SKU', ''),
                        'quantity': line.get('Quantity', 0),
                        'description': line.get('Name', '')
                    })
            
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
    """Sync recent sales data for velocity calculation"""
    try:
        # Fetch recent orders
        orders = cin7.fetch_recent_orders(days=60)  # Get 60 days of data
        
        conn = get_db()
        cursor = conn.cursor()
        
        total_lines = 0
        
        # For each order, get the detailed lines
        for i, order in enumerate(orders[:10]):  # Limit to 10 orders for testing
            logger.info(f"Processing order {i+1}/{min(10, len(orders))}: {order['order_number']}")
            
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
            import time
            time.sleep(2)  # Rate limiting
        
        conn.close()
        
        return jsonify({
            'success': True,
            'orders_processed': min(10, len(orders)),
            'total_orders_found': len(orders),
            'lines_stored': total_lines,
            'message': 'Sales data synced successfully'
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

@app.route('/reorder-analysis')
def reorder_analysis():
    """Calculate reorder points for all SKUs"""
    try:
        # Get parameters
        lead_time_days = int(request.args.get('lead_time', 30))
        service_level = float(request.args.get('service_level', 95))  # 95% service level
        review_days = int(request.args.get('review_days', 7))  # Weekly review
        
        conn = get_db()
        cursor = conn.cursor()
        
        # Get all SKUs with sales
        cursor.execute('''
            SELECT DISTINCT sku 
            FROM sales 
            WHERE sale_date >= date('now', '-90 days')
        ''')
        
        skus = [row['sku'] for row in cursor.fetchall()]
        
        reorder_data = []
        
        for sku in skus:
            # Calculate 30-day velocity
            cursor.execute('''
                SELECT SUM(quantity) as total_qty
                FROM sales 
                WHERE sku = ? 
                AND sale_date >= date('now', '-30 days')
            ''', (sku,))
            
            result = cursor.fetchone()
            total_qty = result['total_qty'] or 0
            daily_velocity = total_qty / 30
            
            # Get current stock (mock data for now - would come from Cin7 stock API)
            current_stock = 100  # Placeholder - replace with actual stock lookup
            
            # Calculate reorder point
            # Formula: (Lead Time + Review Period) × Daily Velocity + Safety Stock
            demand_during_lead_time = (lead_time_days + review_days) * daily_velocity
            
            # Simple safety stock calculation (can be enhanced)
            # For 95% service level, use ~1.65 standard deviations
            safety_factor = 1.65 if service_level >= 95 else 1.28
            safety_stock = safety_factor * daily_velocity * (lead_time_days ** 0.5)
            
            reorder_point = demand_during_lead_time + safety_stock
            
            # Recommended order quantity (simple EOQ approximation)
            # Order for lead time + review period + safety stock
            recommended_qty = max(0, reorder_point - current_stock)
            
            # Get product description
            cursor.execute('SELECT description FROM products WHERE sku = ?', (sku,))
            product = cursor.fetchone()
            
            reorder_data.append({
                'sku': sku,
                'description': product['description'] if product else '',
                'current_stock': current_stock,
                'daily_velocity': round(daily_velocity, 2),
                'reorder_point': round(reorder_point, 0),
                'safety_stock': round(safety_stock, 0),
                'recommended_order_qty': round(recommended_qty, 0),
                'needs_reorder': current_stock < reorder_point,
                'days_until_stockout': round(current_stock / daily_velocity, 0) if daily_velocity > 0 else 999
            })
        
        # Sort by urgency (lowest days until stockout first)
        reorder_data.sort(key=lambda x: x['days_until_stockout'])
        
        conn.close()
        
        return jsonify({
            'success': True,
            'parameters': {
                'lead_time_days': lead_time_days,
                'service_level': service_level,
                'review_days': review_days
            },
            'total_skus': len(reorder_data),
            'needs_reorder': len([x for x in reorder_data if x['needs_reorder']]),
            'data': reorder_data
        })
        
    except Exception as e:
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
    init_db()
    app.run(debug=True, port=5000)
