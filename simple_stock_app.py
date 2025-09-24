"""
Simple Stock Forecasting App - Business Owner Focused
Clear inputs, clear outputs, actionable decisions
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

def get_db():
    """Get database connection"""
    conn = sqlite3.connect('stock_forecast.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def dashboard():
    """Main dashboard"""
    return render_template('simple_dashboard.html')

@app.route('/api/dashboard/overview')
def dashboard_overview():
    """Simple dashboard overview"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Basic counts
        cursor.execute('SELECT COUNT(*) FROM products')
        total_skus = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM orders')
        total_orders = cursor.fetchone()[0]
        
        # Data freshness
        cursor.execute('SELECT MAX(booking_date) as latest_order FROM orders')
        latest_order = cursor.fetchone()['latest_order']
        
        conn.close()
        
        return jsonify({
            'total_skus': total_skus,
            'total_orders': total_orders,
            'latest_data': latest_order,
            'status': 'ready'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/stock/analysis')
def stock_analysis():
    """Main stock analysis with business-friendly inputs"""
    try:
        # Business owner inputs
        lead_time_days = int(request.args.get('lead_time', 30))
        buffer_months = float(request.args.get('buffer_months', 1))
        growth_rate = float(request.args.get('growth_rate', 0))  # % monthly growth
        
        conn = get_db()
        cursor = conn.cursor()
        
        # Get sales data (using broad date range to include our 2024 data)
        cursor.execute('''
            SELECT 
                sku,
                SUM(quantity) as total_quantity,
                COUNT(*) as order_count,
                MIN(booking_date) as first_sale,
                MAX(booking_date) as last_sale
            FROM orders 
            WHERE booking_date >= date('now', '-500 days')
            GROUP BY sku
            HAVING total_quantity > 0
            ORDER BY total_quantity DESC
        ''')
        
        analysis_data = []
        
        for row in cursor.fetchall():
            sku = row['sku']
            total_qty = row['total_quantity']
            
            # Calculate actual sales velocity
            if row['first_sale'] and row['last_sale']:
                first_date = datetime.strptime(row['first_sale'], '%Y-%m-%d')
                last_date = datetime.strptime(row['last_sale'], '%Y-%m-%d')
                actual_days = (last_date - first_date).days + 1
            else:
                actual_days = 1
            
            daily_velocity = total_qty / actual_days
            monthly_velocity = daily_velocity * 30
            
            # Apply growth rate to velocity
            adjusted_monthly_velocity = monthly_velocity * (1 + growth_rate / 100)
            adjusted_daily_velocity = adjusted_monthly_velocity / 30
            
            # Calculate current stock (mock for now)
            current_stock = max(0, 100 - total_qty)  # Mock: started with 100, subtract sales
            
            # Simple reorder calculation
            lead_time_demand = lead_time_days * adjusted_daily_velocity
            buffer_stock = buffer_months * adjusted_monthly_velocity
            reorder_point = lead_time_demand + buffer_stock
            
            # How much to order
            order_quantity = max(0, reorder_point - current_stock)
            
            # Days until stockout
            days_until_stockout = current_stock / adjusted_daily_velocity if adjusted_daily_velocity > 0 else 999
            
            # Simple status
            if days_until_stockout <= lead_time_days:
                status = 'URGENT'
                status_color = 'red'
            elif current_stock < reorder_point:
                status = 'REORDER NEEDED'
                status_color = 'orange'
            else:
                status = 'OK'
                status_color = 'green'
            
            # Get description
            cursor.execute('SELECT description FROM products WHERE sku = ?', (sku,))
            product = cursor.fetchone()
            
            analysis_data.append({
                'sku': sku,
                'description': product['description'] if product else '',
                'current_stock': round(current_stock, 0),
                'daily_velocity': round(adjusted_daily_velocity, 2),
                'monthly_velocity': round(adjusted_monthly_velocity, 1),
                'reorder_point': round(reorder_point, 0),
                'order_quantity': round(order_quantity, 0),
                'days_until_stockout': round(days_until_stockout, 0),
                'status': status,
                'status_color': status_color,
                'lead_time_demand': round(lead_time_demand, 1),
                'buffer_stock': round(buffer_stock, 1)
            })
        
        # Sort by urgency (lowest days until stockout first)
        analysis_data.sort(key=lambda x: x['days_until_stockout'])
        
        conn.close()
        
        # Summary stats
        total_skus = len(analysis_data)
        needs_reorder = len([x for x in analysis_data if x['status'] != 'OK'])
        urgent_items = len([x for x in analysis_data if x['status'] == 'URGENT'])
        
        return jsonify({
            'success': True,
            'parameters': {
                'lead_time_days': lead_time_days,
                'buffer_months': buffer_months,
                'growth_rate': growth_rate
            },
            'summary': {
                'total_skus': total_skus,
                'needs_reorder': needs_reorder,
                'urgent_items': urgent_items
            },
            'data': analysis_data
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/sku/<sku>/forecast')
def sku_forecast(sku):
    """Simple forecast for a specific SKU"""
    try:
        months_ahead = int(request.args.get('months', 6))
        growth_rate = float(request.args.get('growth_rate', 0))
        
        conn = get_db()
        cursor = conn.cursor()
        
        # Get velocity for this SKU
        cursor.execute('''
            SELECT 
                SUM(quantity) as total_quantity,
                MIN(booking_date) as first_sale,
                MAX(booking_date) as last_sale
            FROM orders 
            WHERE sku = ? 
            AND booking_date >= date('now', '-500 days')
        ''', (sku,))
        
        result = cursor.fetchone()
        
        if not result or not result['total_quantity']:
            return jsonify({
                'sku': sku,
                'error': 'No sales data found'
            })
        
        # Calculate velocity
        if result['first_sale'] and result['last_sale']:
            first_date = datetime.strptime(result['first_sale'], '%Y-%m-%d')
            last_date = datetime.strptime(result['last_sale'], '%Y-%m-%d')
            actual_days = (last_date - first_date).days + 1
        else:
            actual_days = 1
        
        daily_velocity = result['total_quantity'] / actual_days
        monthly_velocity = daily_velocity * 30
        
        # Apply growth rate
        adjusted_monthly_velocity = monthly_velocity * (1 + growth_rate / 100)
        
        # Mock current stock
        current_stock = max(0, 100 - result['total_quantity'])
        
        # Generate monthly forecast
        forecast = []
        projected_stock = current_stock
        
        for month in range(1, months_ahead + 1):
            projected_consumption = adjusted_monthly_velocity * month
            projected_stock = max(0, current_stock - projected_consumption)
            
            forecast.append({
                'month': month,
                'projected_stock': round(projected_stock, 0),
                'monthly_consumption': round(adjusted_monthly_velocity, 1),
                'stockout_risk': projected_stock <= 0
            })
        
        # Find stockout month
        stockout_month = next((f['month'] for f in forecast if f['stockout_risk']), None)
        
        conn.close()
        
        return jsonify({
            'sku': sku,
            'current_stock': current_stock,
            'monthly_velocity': round(adjusted_monthly_velocity, 1),
            'stockout_in_months': stockout_month,
            'forecast': forecast
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    print("🚀 Simple Stock Forecasting App")
    print("👔 Business Owner Focused")
    print("📊 Dashboard: http://localhost:5005")
    print("\n🎯 Core Features:")
    print("  - Clear reorder recommendations")
    print("  - Simple business inputs")
    print("  - Actionable purchasing decisions")
    
    app.run(debug=True, port=5005)
