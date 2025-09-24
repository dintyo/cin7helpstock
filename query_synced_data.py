"""
Query our synced database for OB-ESS-Q and related SKUs
"""
import sqlite3
from datetime import datetime

DATABASE = 'stock_forecast.db'

def query_ob_skus():
    """Query database for OB-related SKUs"""
    try:
        conn = sqlite3.connect(DATABASE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        print("🔍 Querying synced database for OB-ESS-Q and related SKUs")
        print("=" * 60)
        
        # Check total data synced
        cursor.execute('SELECT COUNT(*) as total_orders FROM orders')
        total_orders = cursor.fetchone()['total_orders']
        
        cursor.execute('SELECT COUNT(DISTINCT sku) as unique_skus FROM orders')
        unique_skus = cursor.fetchone()['unique_skus']
        
        print(f"📊 Database contains:")
        print(f"   📦 Total order lines: {total_orders}")
        print(f"   🏷️ Unique SKUs: {unique_skus}")
        
        # Check for exact OB-ESS-Q match
        print(f"\n🎯 Checking for exact 'OB-ESS-Q' match...")
        cursor.execute('''
            SELECT sku, SUM(quantity) as total_qty, COUNT(*) as order_count,
                   MIN(booking_date) as first_order, MAX(booking_date) as last_order
            FROM orders 
            WHERE sku = 'OB-ESS-Q'
            GROUP BY sku
        ''')
        
        exact_match = cursor.fetchone()
        if exact_match:
            print(f"   ✅ FOUND OB-ESS-Q!")
            print(f"   📈 Total quantity: {exact_match['total_qty']}")
            print(f"   📋 Number of orders: {exact_match['order_count']}")
            print(f"   📅 Date range: {exact_match['first_order']} to {exact_match['last_order']}")
            
            # Calculate velocity
            if exact_match['first_order'] and exact_match['last_order']:
                first_date = datetime.strptime(exact_match['first_order'], '%Y-%m-%d')
                last_date = datetime.strptime(exact_match['last_order'], '%Y-%m-%d')
                actual_days = (last_date - first_date).days + 1
                daily_velocity = exact_match['total_qty'] / actual_days
                
                print(f"\n📈 OB-ESS-Q Sales Velocity:")
                print(f"   Daily: {daily_velocity:.3f} units/day")
                print(f"   Weekly: {daily_velocity * 7:.2f} units/week")
                print(f"   Monthly: {daily_velocity * 30:.1f} units/month")
        else:
            print(f"   ❌ No exact 'OB-ESS-Q' found")
        
        # Check for all OB-related SKUs
        print(f"\n🔍 All OB-related SKUs in database:")
        cursor.execute('''
            SELECT sku, SUM(quantity) as total_qty, COUNT(*) as order_count
            FROM orders 
            WHERE sku LIKE '%OB%'
            GROUP BY sku
            ORDER BY total_qty DESC
        ''')
        
        ob_skus = cursor.fetchall()
        if ob_skus:
            print(f"   📦 Found {len(ob_skus)} OB-related SKUs:")
            for sku_row in ob_skus:
                print(f"   - {sku_row['sku']}: {sku_row['total_qty']} units ({sku_row['order_count']} orders)")
        else:
            print(f"   ❌ No OB-related SKUs found")
        
        # Check for potential matches (case insensitive, partial)
        print(f"\n🔍 Potential OB-ESS-Q matches (case insensitive):")
        cursor.execute('''
            SELECT sku, SUM(quantity) as total_qty, COUNT(*) as order_count
            FROM orders 
            WHERE UPPER(sku) LIKE '%OB%ESS%' OR UPPER(sku) LIKE '%OB-ESS%'
            GROUP BY sku
            ORDER BY total_qty DESC
        ''')
        
        potential_matches = cursor.fetchall()
        if potential_matches:
            for match in potential_matches:
                print(f"   🎯 {match['sku']}: {match['total_qty']} units ({match['order_count']} orders)")
        else:
            print(f"   ❌ No potential ESS matches found")
        
        # Show top 10 SKUs for context
        print(f"\n📊 Top 10 most sold SKUs (for context):")
        cursor.execute('''
            SELECT sku, SUM(quantity) as total_qty, COUNT(*) as order_count
            FROM orders 
            GROUP BY sku
            ORDER BY total_qty DESC
            LIMIT 10
        ''')
        
        top_skus = cursor.fetchall()
        for i, sku_row in enumerate(top_skus, 1):
            print(f"   {i}. {sku_row['sku']}: {sku_row['total_qty']} units ({sku_row['order_count']} orders)")
        
        # Check date range of synced data
        print(f"\n📅 Date range of synced data:")
        cursor.execute('SELECT MIN(booking_date) as first_date, MAX(booking_date) as last_date FROM orders')
        date_range = cursor.fetchone()
        print(f"   📅 From: {date_range['first_date']}")
        print(f"   📅 To: {date_range['last_date']}")
        
        conn.close()
        
        return exact_match is not None
        
    except Exception as e:
        print(f"❌ Database query failed: {e}")
        return False

if __name__ == '__main__':
    print("🔍 OB-ESS-Q Database Analysis")
    print("📊 Analyzing synced customer order data")
    print()
    
    found = query_ob_skus()
    
    print(f"\n" + "=" * 60)
    print(f"🎯 RESULT: OB-ESS-Q {'FOUND' if found else 'NOT FOUND'} in synced data")
    print(f"💾 Data source: Local SQLite database (last 10 days synced)")
