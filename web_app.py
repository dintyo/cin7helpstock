"""
Stock Forecasting Web Application
Professional web interface for stock forecasting and reorder management
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

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_db():
    """Get database connection"""
    conn = sqlite3.connect('stock_forecast.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def dashboard():
    """Main dashboard"""
    return render_template('dashboard.html')

@app.route('/api/dashboard/stats')
def dashboard_stats():
    """Get dashboard statistics"""
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
        
        # Date range of data
        cursor.execute('SELECT MIN(booking_date) as min_date, MAX(booking_date) as max_date FROM orders')
        date_range = cursor.fetchone()
        
        # Recent activity
        cursor.execute('''
            SELECT COUNT(*) FROM orders 
            WHERE booking_date >= date('now', '-30 days')
        ''')
        recent_orders = cursor.fetchone()[0]
        
        conn.close()
        
        return jsonify({
            'total_skus': total_skus,
            'total_orders': total_orders,
            'active_skus': active_skus,
            'recent_orders_30d': recent_orders,
            'data_range': {
                'from': date_range['min_date'],
                'to': date_range['max_date']
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/skus/velocity')
def skus_velocity():
    """Get velocity data for all SKUs"""
    try:
        days = int(request.args.get('days', 30))
        warehouse = request.args.get('warehouse')
        
        conn = get_db()
        cursor = conn.cursor()
        
        # Get all SKUs with sales
        where_clause = 'WHERE booking_date >= date("now", "-{} days")'.format(days)
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
            ORDER BY total_quantity DESC
        ''', params)
        
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
            'period_days': days,
            'warehouse': warehouse or 'ALL',
            'total_skus': len(velocity_data),
            'data': velocity_data
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/reorder/calculate')
def calculate_reorder_points():
    """Calculate reorder points with user parameters"""
    try:
        # Get user inputs
        lead_time_days = int(request.args.get('lead_time', 30))
        service_level = float(request.args.get('service_level', 95))
        review_days = int(request.args.get('review_days', 7))
        warehouse = request.args.get('warehouse')
        
        conn = get_db()
        cursor = conn.cursor()
        
        # Get velocity data for calculation period
        velocity_days = 60  # Use 60 days for velocity calculation
        
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
            
            # Mock current stock (TODO: integrate with Cin7 stock API)
            current_stock = 50  # Placeholder
            
            # Calculate reorder point using proven formula
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
                'velocity_period': f"{row['first_sale']} to {row['last_sale']}"
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
                'warehouse': warehouse or 'ALL'
            },
            'total_skus': len(reorder_data),
            'needs_reorder': len([x for x in reorder_data if x['needs_reorder']]),
            'data': reorder_data
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/forecast/<sku>')
def forecast_sku(sku):
    """Generate simple forecast for a SKU"""
    try:
        days_ahead = int(request.args.get('days', 90))
        
        conn = get_db()
        cursor = conn.cursor()
        
        # Get velocity (last 60 days)
        cursor.execute('''
            SELECT 
                SUM(quantity) as total_quantity,
                MIN(booking_date) as first_sale,
                MAX(booking_date) as last_sale
            FROM orders 
            WHERE sku = ? 
            AND booking_date >= date('now', '-60 days')
        ''', (sku,))
        
        result = cursor.fetchone()
        
        if not result or not result['total_quantity']:
            return jsonify({
                'sku': sku,
                'error': 'No sales data found',
                'daily_velocity': 0
            })
        
        # Calculate velocity
        if result['first_sale'] and result['last_sale']:
            first_date = datetime.strptime(result['first_sale'], '%Y-%m-%d')
            last_date = datetime.strptime(result['last_sale'], '%Y-%m-%d')
            actual_days = (last_date - first_date).days + 1
        else:
            actual_days = 1
        
        daily_velocity = result['total_quantity'] / actual_days
        
        # Mock current stock
        current_stock = 50  # TODO: Get from Cin7 stock API
        
        # Generate forecast
        forecast = []
        for day in range(1, days_ahead + 1):
            projected_stock = current_stock - (daily_velocity * day)
            forecast_date = (datetime.now() + timedelta(days=day)).strftime('%Y-%m-%d')
            
            forecast.append({
                'day': day,
                'date': forecast_date,
                'projected_stock': max(0, round(projected_stock, 1)),
                'stockout_risk': projected_stock <= 0
            })
        
        # Find stockout date
        stockout_day = next((f['day'] for f in forecast if f['stockout_risk']), None)
        
        conn.close()
        
        return jsonify({
            'success': True,
            'sku': sku,
            'current_stock': current_stock,
            'daily_velocity': round(daily_velocity, 2),
            'stockout_in_days': stockout_day,
            'forecast_days': days_ahead,
            'forecast': forecast[:30]  # First 30 days for display
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    print("🚀 Stock Forecasting Web App")
    print("📊 Dashboard: http://localhost:5003")
    print("🔧 Building web interface...")
    
    app.run(debug=True, port=5003)
