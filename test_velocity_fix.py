"""
Test the corrected velocity calculation
"""
import sqlite3
from datetime import datetime

conn = sqlite3.connect('stock_forecast.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

print('=== CORRECTED VELOCITY CALCULATION ===')
cursor.execute("""
    SELECT 
        SUM(quantity) as total_quantity,
        COUNT(*) as order_count,
        MIN(booking_date) as first_sale,
        MAX(booking_date) as last_sale
    FROM orders 
    WHERE sku = 'OBQ'
    AND booking_date BETWEEN '2024-06-04' AND '2024-06-04'
""")

result = cursor.fetchone()
if result:
    total_qty = result['total_quantity'] or 0
    first_date = datetime.strptime(result['first_sale'], '%Y-%m-%d')
    last_date = datetime.strptime(result['last_sale'], '%Y-%m-%d')
    actual_days = (last_date - first_date).days + 1
    
    print(f'Total quantity: {total_qty}')
    print(f'Actual sales period: {actual_days} days')
    print(f'CORRECTED daily velocity: {total_qty / actual_days}')
    print(f'This means: {total_qty} units sold in {actual_days} day(s)')
    print()
    print('🎯 KEY INSIGHT: All 3 OBQ orders happened on the SAME DAY!')
    print('   This is concentrated demand, not steady daily sales.')
    print('   For forecasting, we need longer periods with regular sales.')

conn.close()
