"""
Debug velocity calculation issue
"""
import sqlite3
from datetime import datetime

def debug_velocity():
    print("🔍 Debugging velocity calculation...")
    
    conn = sqlite3.connect('stock_forecast.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    print("\n=== OBQ ORDERS ===")
    cursor.execute('SELECT sku, quantity, booking_date, order_number FROM orders WHERE sku = "OBQ"')
    orders = cursor.fetchall()
    for order in orders:
        print(f"SKU: {order['sku']}, Qty: {order['quantity']}, Date: {order['booking_date']}, Order: {order['order_number']}")
    
    print("\n=== DATE CALCULATION CHECK ===")
    cursor.execute('SELECT COUNT(*) as count FROM orders WHERE sku = "OBQ" AND booking_date >= date("now", "-500 days")')
    result = cursor.fetchone()
    print(f"Orders in last 500 days: {result['count']}")
    
    cursor.execute('SELECT COUNT(*) as count FROM orders WHERE sku = "OBQ" AND booking_date >= date("now", "-30 days")')
    result = cursor.fetchone()
    print(f"Orders in last 30 days: {result['count']}")
    
    print("\n=== CURRENT DATE vs ORDER DATES ===")
    current_date = datetime.now().strftime('%Y-%m-%d')
    print(f"Current date: {current_date}")
    cursor.execute('SELECT DISTINCT booking_date FROM orders ORDER BY booking_date')
    dates = cursor.fetchall()
    print(f"Order dates in DB: {[d['booking_date'] for d in dates]}")
    
    print("\n=== VELOCITY CALCULATION BREAKDOWN ===")
    # Simulate the velocity calculation
    cursor.execute('''
        SELECT 
            SUM(quantity) as total_quantity,
            COUNT(*) as order_count,
            MIN(booking_date) as first_sale,
            MAX(booking_date) as last_sale
        FROM orders 
        WHERE sku = "OBQ" 
        AND booking_date >= date("now", "-500 days")
    ''')
    
    result = cursor.fetchone()
    if result:
        total_qty = result['total_quantity'] or 0
        print(f"Total quantity: {total_qty}")
        print(f"Order count: {result['order_count']}")
        print(f"First sale: {result['first_sale']}")
        print(f"Last sale: {result['last_sale']}")
        print(f"WRONG calculation: {total_qty} / 500 days = {total_qty / 500}")
        
        # What it SHOULD be - all orders on same day!
        if result['first_sale'] and result['last_sale']:
            first_date = datetime.strptime(result['first_sale'], '%Y-%m-%d')
            last_date = datetime.strptime(result['last_sale'], '%Y-%m-%d')
            actual_days = (last_date - first_date).days + 1
            print(f"CORRECT calculation: {total_qty} / {actual_days} actual days = {total_qty / actual_days}")
            print(f"All orders on same day = concentrated sales, not spread over 500 days!")
    
    conn.close()

if __name__ == '__main__':
    debug_velocity()
