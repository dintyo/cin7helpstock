"""
Enhanced Stock Forecasting Web App
Using calculated stock levels (like example app) until we find correct Cin7 stock API
"""
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv
import sqlite3
import os
from datetime import datetime, timedelta
import logging

load_dotenv()

app = Flask(__name__)
CORS(app)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_db():
    """Get database connection"""
    conn = sqlite3.connect('stock_forecast.db')
    conn.row_factory = sqlite3.Row
    return conn

def calculate_stock_on_hand():
    """Calculate stock on hand from orders (like example app does)"""
    conn = get_db()
    cursor = conn.cursor()
    
    # For now, we'll simulate arrivals since we don't have arrival data
    # In real implementation, this would be: arrivals - orders
    cursor.execute('''
        SELECT 
            sku,
            SUM(quantity) as total_sold,
            COUNT(*) as order_count,
            MAX(booking_date) as last_sale
        FROM orders
        GROUP BY sku
    ''')
    
    stock_levels = {}
    for row in cursor.fetchall():
        sku = row['sku']
        total_sold = row['total_sold']
        
        # Mock calculation: assume we had 100 units initially, subtract sales
        # In real app, this would be actual arrivals - orders
        mock_initial_stock = 100
        calculated_stock = max(0, mock_initial_stock - total_sold)
        
        stock_levels[sku] = {
            'on_hand': calculated_stock,
            'total_sold': total_sold,
            'order_count': row['order_count'],
            'last_sale': row['last_sale'],
            'mock_data': True  # Flag to indicate this is calculated
        }
    
    conn.close()
    return stock_levels

@app.route('/')
def dashboard():
    """Main dashboard"""
    return render_template('enhanced_dashboard.html')

@app.route('/api/dashboard/stats')
def dashboard_stats():
    """Enhanced dashboard statistics"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Basic stats
        cursor.execute('SELECT COUNT(*) FROM products')
        total_skus = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM orders')
        total_orders = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(DISTINCT sku) FROM orders')
        active_skus = cursor.fetchone()[0]
        
        # Date range
        cursor.execute('SELECT MIN(booking_date) as min_date, MAX(booking_date) as max_date FROM orders')
        date_range = cursor.fetchone()
        
        # Warehouse breakdown
        cursor.execute('''
            SELECT 
                warehouse,
                COUNT(*) as order_count,
                SUM(quantity) as total_quantity
            FROM orders 
            GROUP BY warehouse
        ''')
        
        warehouse_stats = []
        for row in cursor.fetchall():
            warehouse_stats.append({
                'warehouse': row['warehouse'],
                'orders': row['order_count'],
                'total_quantity': row['total_quantity']
            })
        
        conn.close()
        
        return jsonify({
            'total_skus': total_skus,
            'total_orders': total_orders,
            'active_skus': active_skus,
            'data_range': {
                'from': date_range['min_date'],
                'to': date_range['max_date']
            },
            'warehouse_breakdown': warehouse_stats
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/reorder/calculate')
def calculate_reorder_points():
    """Calculate reorder points with real stock levels"""
    try:
        # Get user inputs
        lead_time_days = int(request.args.get('lead_time', 30))
        service_level = float(request.args.get('service_level', 95))
        review_days = int(request.args.get('review_days', 7))
        warehouse = request.args.get('warehouse')
        velocity_days = int(request.args.get('velocity_days', 60))
        
        # Get calculated stock levels
        stock_levels = calculate_stock_on_hand()
        
        conn = get_db()
        cursor = conn.cursor()
        
        # Get velocity data
        where_clause = 'WHERE booking_date >= date("now", "-{} days")'.format(velocity_days)
        params = []
        
        if warehouse:
            where_clause += ' AND warehouse = ?'
            params.append(warehouse)
        
        cursor.execute(f'''
            SELECT 
                sku,
                SUM(quantity) as total_quantity,
                COUNT(*) as order_count,
                MIN(booking_date) as first_sale,
                MAX(booking_date) as last_sale
            FROM orders 
            {where_clause}
            GROUP BY sku
            HAVING total_quantity > 0
        ''', params)
        
        reorder_data = []
        
        for row in cursor.fetchall():
            sku = row['sku']
            total_qty = row['total_quantity']
            
            # Calculate velocity based on actual sales period
            if row['first_sale'] and row['last_sale']:
                first_date = datetime.strptime(row['first_sale'], '%Y-%m-%d')
                last_date = datetime.strptime(row['last_sale'], '%Y-%m-%d')
                actual_days = (last_date - first_date).days + 1
            else:
                actual_days = 1
            
            daily_velocity = total_qty / actual_days
            
            # Get current stock (calculated or mock)
            current_stock = stock_levels.get(sku, {}).get('on_hand', 50)
            
            # Calculate reorder point
            demand_during_lead_time = (lead_time_days + review_days) * daily_velocity
            
            # Safety stock calculation
            safety_factor = 1.65 if service_level >= 95 else 1.28
            safety_stock = safety_factor * daily_velocity * (lead_time_days ** 0.5)
            
            reorder_point = demand_during_lead_time + safety_stock
            recommended_qty = max(0, reorder_point - current_stock)
            
            # Get description
            cursor.execute('SELECT description FROM products WHERE sku = ?', (sku,))
            product = cursor.fetchone()
            
            reorder_data.append({
                'sku': sku,
                'description': product['description'] if product else '',
                'current_stock': current_stock,
                'daily_velocity': round(daily_velocity, 2),
                'demand_during_lead_time': round(demand_during_lead_time, 1),
                'safety_stock': round(safety_stock, 1),
                'reorder_point': round(reorder_point, 0),
                'recommended_order_qty': round(recommended_qty, 0),
                'needs_reorder': current_stock < reorder_point,
                'days_until_stockout': round(current_stock / daily_velocity, 0) if daily_velocity > 0 else 999,
                'order_count': row['order_count'],
                'velocity_period': f"{row['first_sale']} to {row['last_sale']}",
                'stock_source': 'calculated'  # Indicate this is calculated, not real-time
            })
        
        # Sort by urgency
        reorder_data.sort(key=lambda x: x['days_until_stockout'])
        
        conn.close()
        
        return jsonify({
            'success': True,
            'parameters': {
                'lead_time_days': lead_time_days,
                'service_level': service_level,
                'review_days': review_days,
                'velocity_days': velocity_days,
                'warehouse': warehouse or 'ALL'
            },
            'total_skus': len(reorder_data),
            'needs_reorder': len([x for x in reorder_data if x['needs_reorder']]),
            'data': reorder_data,
            'note': 'Stock levels are calculated (mock data). Real Cin7 stock integration pending.'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/skus/velocity')
def skus_velocity():
    """Get velocity data for all SKUs with flexible date ranges"""
    try:
        # Support both days back and specific date ranges
        start_date = request.args.get('start')
        end_date = request.args.get('end')
        days = int(request.args.get('days', 60))
        warehouse = request.args.get('warehouse')
        
        conn = get_db()
        cursor = conn.cursor()
        
        # Build date filter
        if start_date and end_date:
            date_filter = 'WHERE booking_date BETWEEN ? AND ?'
            date_params = [start_date, end_date]
            period_desc = f"{start_date} to {end_date}"
        else:
            date_filter = 'WHERE booking_date >= date("now", "-{} days")'.format(days)
            date_params = []
            period_desc = f"last {days} days"
        
        # Add warehouse filter
        if warehouse:
            date_filter += ' AND warehouse = ?'
            date_params.append(warehouse)
        
        cursor.execute(f'''
            SELECT 
                sku,
                SUM(quantity) as total_quantity,
                COUNT(*) as order_count,
                MIN(booking_date) as first_sale,
                MAX(booking_date) as last_sale
            FROM orders 
            {date_filter}
            GROUP BY sku
            ORDER BY total_quantity DESC
        ''', date_params)
        
        velocity_data = []
        for row in cursor.fetchall():
            # Calculate actual sales period
            if row['first_sale'] and row['last_sale']:
                first_date = datetime.strptime(row['first_sale'], '%Y-%m-%d')
                last_date = datetime.strptime(row['last_sale'], '%Y-%m-%d')
                actual_days = (last_date - first_date).days + 1
            else:
                actual_days = 1
            
            daily_velocity = row['total_quantity'] / actual_days
            
            # Get product description
            cursor.execute('SELECT description FROM products WHERE sku = ?', (row['sku'],))
            product = cursor.fetchone()
            
            velocity_data.append({
                'sku': row['sku'],
                'description': product['description'] if product else '',
                'total_quantity': row['total_quantity'],
                'order_count': row['order_count'],
                'actual_days': actual_days,
                'daily_velocity': round(daily_velocity, 2),
                'weekly_velocity': round(daily_velocity * 7, 2),
                'monthly_velocity': round(daily_velocity * 30, 2),
                'first_sale': row['first_sale'],
                'last_sale': row['last_sale']
            })
        
        conn.close()
        
        return jsonify({
            'success': True,
            'period': period_desc,
            'warehouse': warehouse or 'ALL',
            'total_skus': len(velocity_data),
            'data': velocity_data
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/sku/<sku>/config', methods=['GET', 'POST'])
def sku_config(sku):
    """Get or update SKU-specific configuration"""
    conn = get_db()
    cursor = conn.cursor()
    
    if request.method == 'GET':
        # Get current config
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sku_config (
                sku TEXT PRIMARY KEY,
                lead_time_days INTEGER DEFAULT 30,
                buffer_stock_days INTEGER DEFAULT 30,
                min_order_qty REAL DEFAULT 1,
                supplier TEXT,
                notes TEXT,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('SELECT * FROM sku_config WHERE sku = ?', (sku,))
        config = cursor.fetchone()
        
        if config:
            result = dict(config)
        else:
            # Default config
            result = {
                'sku': sku,
                'lead_time_days': 30,
                'buffer_stock_days': 30,
                'min_order_qty': 1,
                'supplier': '',
                'notes': ''
            }
        
        conn.close()
        return jsonify(result)
    
    elif request.method == 'POST':
        # Update config
        data = request.get_json()
        
        cursor.execute('''
            INSERT OR REPLACE INTO sku_config 
            (sku, lead_time_days, buffer_stock_days, min_order_qty, supplier, notes, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            sku,
            data.get('lead_time_days', 30),
            data.get('buffer_stock_days', 30),
            data.get('min_order_qty', 1),
            data.get('supplier', ''),
            data.get('notes', ''),
            datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': f'Configuration updated for {sku}'})

if __name__ == '__main__':
    print("🚀 Enhanced Stock Forecasting Web App")
    print("📊 Dashboard: http://localhost:5004")
    print("🔧 Features: Velocity + Reorder Points + SKU Config")
    print("📝 Note: Using calculated stock levels (arrivals-orders)")
    
    app.run(debug=True, port=5004)
