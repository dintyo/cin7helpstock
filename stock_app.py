"""
Stock Forecasting App - Using proven sync patterns from example app
"""
import os
from flask import Flask, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv
from datetime import datetime, timedelta
import sqlite3
import logging

from sync_manager import SyncManager

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

# Initialize sync manager
sync_manager = SyncManager()

def get_db():
    """Get database connection"""
    conn = sqlite3.connect('stock_forecast.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/health')
def health():
    return jsonify({
        'status': 'healthy', 
        'timestamp': datetime.now().isoformat(),
        'database': 'sqlite'
    })

@app.route('/sync/status')
def sync_status():
    """Get current sync status"""
    status = sync_manager.get_sync_status()
    return jsonify(status)

@app.route('/sync/test-week')
def sync_test_week():
    """Sync a week of orders for testing (DRY RUN by default)"""
    dry_run = request.args.get('apply') != 'true'
    days = int(request.args.get('days', 7))
    
    logger.info(f"Starting {'DRY RUN' if dry_run else 'LIVE'} sync for last {days} days")
    
    result = sync_manager.sync_week_of_orders(days_back=days, dry_run=dry_run)
    return jsonify(result)

@app.route('/sync/incremental')
def sync_incremental():
    """Incremental sync from last sync point"""
    dry_run = request.args.get('apply') != 'true'
    max_pages = int(request.args.get('pages', 3))
    
    logger.info(f"Starting {'DRY RUN' if dry_run else 'LIVE'} incremental sync")
    
    result = sync_manager.sync_recent_orders(max_pages=max_pages, dry_run=dry_run)
    return jsonify(result)

@app.route('/velocity/<sku>')
def calculate_velocity(sku):
    """Calculate sales velocity for a SKU"""
    try:
        days = int(request.args.get('days', 30))
        warehouse = request.args.get('warehouse')  # Optional filter
        
        conn = get_db()
        cursor = conn.cursor()
        
        # Build query with optional warehouse filter
        where_clause = 'WHERE sku = ? AND booking_date >= date("now", "-{} days")'.format(days)
        params = [sku]
        
        if warehouse:
            where_clause += ' AND warehouse = ?'
            params.append(warehouse)
        
        cursor.execute(f'''
            SELECT 
                SUM(quantity) as total_quantity,
                COUNT(*) as order_count,
                MIN(booking_date) as first_sale,
                MAX(booking_date) as last_sale
            FROM orders 
            {where_clause}
        ''', params)
        
        result = cursor.fetchone()
        
        if not result or not result['total_quantity']:
            return jsonify({
                'sku': sku,
                'warehouse': warehouse,
                'daily_velocity': 0,
                'weekly_velocity': 0,
                'monthly_velocity': 0,
                'message': 'No sales data found'
            })
        
        total_qty = result['total_quantity']
        daily_velocity = total_qty / days
        
        # Get product info
        cursor.execute('SELECT description FROM products WHERE sku = ?', (sku,))
        product = cursor.fetchone()
        
        conn.close()
        
        return jsonify({
            'sku': sku,
            'warehouse': warehouse or 'ALL',
            'description': product['description'] if product else '',
            'period_days': days,
            'total_quantity_sold': total_qty,
            'order_count': result['order_count'],
            'daily_velocity': round(daily_velocity, 2),
            'weekly_velocity': round(daily_velocity * 7, 2),
            'monthly_velocity': round(daily_velocity * 30, 2),
            'first_sale': result['first_sale'],
            'last_sale': result['last_sale']
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/reorder-points')
def calculate_reorder_points():
    """Calculate reorder points for all active SKUs"""
    try:
        # Get parameters
        lead_time_days = int(request.args.get('lead_time', 30))
        service_level = float(request.args.get('service_level', 95))
        review_days = int(request.args.get('review_days', 7))
        warehouse = request.args.get('warehouse')  # Optional filter
        
        conn = get_db()
        cursor = conn.cursor()
        
        # Get all SKUs with recent sales
        where_clause = 'WHERE booking_date >= date("now", "-90 days")'
        params = []
        
        if warehouse:
            where_clause += ' AND warehouse = ?'
            params.append(warehouse)
        
        cursor.execute(f'''
            SELECT DISTINCT sku 
            FROM orders 
            {where_clause}
        ''', params)
        
        skus = [row['sku'] for row in cursor.fetchall()]
        
        reorder_data = []
        
        for sku in skus:
            # Calculate 30-day velocity
            velocity_params = [sku]
            velocity_where = 'WHERE sku = ? AND booking_date >= date("now", "-30 days")'
            
            if warehouse:
                velocity_where += ' AND warehouse = ?'
                velocity_params.append(warehouse)
            
            cursor.execute(f'''
                SELECT SUM(quantity) as total_qty, COUNT(*) as order_count
                FROM orders 
                {velocity_where}
            ''', velocity_params)
            
            result = cursor.fetchone()
            total_qty = result['total_qty'] or 0
            order_count = result['order_count'] or 0
            daily_velocity = total_qty / 30
            
            # Mock current stock for MVP (replace with actual Cin7 stock API later)
            current_stock = 50  # Placeholder
            
            # Calculate reorder point (proven formula)
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
                'warehouse': warehouse or 'ALL',
                'current_stock': current_stock,
                'daily_velocity': round(daily_velocity, 2),
                'order_count_30d': order_count,
                'reorder_point': round(reorder_point, 0),
                'safety_stock': round(safety_stock, 0),
                'recommended_order_qty': round(recommended_qty, 0),
                'needs_reorder': current_stock < reorder_point,
                'days_until_stockout': round(current_stock / daily_velocity, 0) if daily_velocity > 0 else 999
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
                'warehouse': warehouse
            },
            'total_skus': len(reorder_data),
            'needs_reorder': len([x for x in reorder_data if x['needs_reorder']]),
            'data': reorder_data
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/data/summary')
def data_summary():
    """Get summary of synced data"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Overall stats
        cursor.execute('SELECT COUNT(*) FROM products')
        total_products = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM orders')
        total_orders = cursor.fetchone()[0]
        
        # Recent activity
        cursor.execute('''
            SELECT 
                warehouse,
                COUNT(*) as order_count,
                SUM(quantity) as total_quantity
            FROM orders 
            WHERE booking_date >= date('now', '-30 days')
            GROUP BY warehouse
        ''')
        
        warehouse_activity = []
        for row in cursor.fetchall():
            warehouse_activity.append({
                'warehouse': row['warehouse'],
                'orders': row['order_count'],
                'total_quantity': row['total_quantity']
            })
        
        # Top SKUs by volume
        cursor.execute('''
            SELECT 
                sku,
                SUM(quantity) as total_quantity,
                COUNT(*) as order_count
            FROM orders 
            WHERE booking_date >= date('now', '-30 days')
            GROUP BY sku
            ORDER BY total_quantity DESC
            LIMIT 10
        ''')
        
        top_skus = []
        for row in cursor.fetchall():
            cursor.execute('SELECT description FROM products WHERE sku = ?', (row['sku'],))
            product = cursor.fetchone()
            
            top_skus.append({
                'sku': row['sku'],
                'description': product['description'] if product else '',
                'total_quantity': row['total_quantity'],
                'order_count': row['order_count']
            })
        
        conn.close()
        
        return jsonify({
            'success': True,
            'summary': {
                'total_products': total_products,
                'total_orders': total_orders,
                'warehouse_activity': warehouse_activity,
                'top_skus_30d': top_skus
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    print("🚀 Stock Forecasting App Starting...")
    print("📊 Database: SQLite")
    print("🔄 Sync: Incremental with state tracking")
    print("🌐 Server: http://localhost:5000")
    print("\n📋 Test Endpoints:")
    print("  GET  /health - Health check")
    print("  GET  /sync/status - Current sync status") 
    print("  GET  /sync/test-week?apply=false - Dry run sync (7 days)")
    print("  GET  /sync/test-week?apply=true&days=3 - Live sync (3 days)")
    print("  GET  /sync/incremental?apply=false - Incremental dry run")
    print("  GET  /velocity/<sku>?warehouse=VIC - Calculate velocity")
    print("  GET  /reorder-points?lead_time=30 - Reorder analysis")
    print("  GET  /data/summary - Data summary")
    
    app.run(debug=True, port=5000)
