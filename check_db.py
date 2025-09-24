"""
Simple database checker script
"""
import sqlite3
from datetime import datetime

def check_database():
    print("🔍 Checking SQLite database...")
    
    conn = sqlite3.connect('stock_forecast.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Check products
    print("\n📦 PRODUCTS:")
    cursor.execute('SELECT * FROM products LIMIT 10')
    products = cursor.fetchall()
    print(f"Total products: {len(products)}")
    for product in products[:5]:
        print(f"  {product['sku']} - {product['description']}")
    
    # Check orders
    print("\n📋 ORDERS:")
    cursor.execute('SELECT * FROM orders LIMIT 10')
    orders = cursor.fetchall()
    print(f"Total orders: {len(orders)}")
    for order in orders[:5]:
        print(f"  {order['order_number']} - {order['sku']} - Qty: {order['quantity']} - Date: {order['booking_date']}")
    
    # Check for OBQ specifically
    print("\n🔍 CHECKING OBQ:")
    cursor.execute('SELECT * FROM products WHERE sku = ?', ('OBQ',))
    obq_product = cursor.fetchone()
    if obq_product:
        print(f"✅ OBQ product found: {obq_product['description']}")
        
        cursor.execute('SELECT * FROM orders WHERE sku = ?', ('OBQ',))
        obq_orders = cursor.fetchall()
        print(f"📊 OBQ orders found: {len(obq_orders)}")
        for order in obq_orders:
            print(f"  Order: {order['order_number']} - Qty: {order['quantity']} - Date: {order['booking_date']}")
    else:
        print("❌ OBQ product not found")
    
    # Check sync state
    print("\n🔄 SYNC STATE:")
    cursor.execute('SELECT * FROM sync_state')
    sync_states = cursor.fetchall()
    for state in sync_states:
        print(f"  {state['sync_type']}: {state['last_sync_timestamp']} (Success: {state['last_sync_success']})")
    
    # Check date range of orders
    print("\n📅 ORDER DATE RANGE:")
    cursor.execute('SELECT MIN(booking_date) as min_date, MAX(booking_date) as max_date FROM orders')
    date_range = cursor.fetchone()
    if date_range and date_range['min_date']:
        print(f"  From: {date_range['min_date']} To: {date_range['max_date']}")
    else:
        print("  No orders found")
    
    conn.close()

if __name__ == '__main__':
    check_database()
