#!/usr/bin/env python3
"""
Database Transfer Script for Render Deployment
Exports local SQLite database to SQL format for production import
"""

import sqlite3
import base64
import os
from datetime import datetime

def export_database_to_sql():
    """Export SQLite database to SQL format"""
    print("🔄 Exporting database to SQL format...")
    
    # Connect to local database
    conn = sqlite3.connect('stock_forecast.db')
    
    # Export to SQL file
    with open('database_export.sql', 'w') as f:
        for line in conn.iterdump():
            f.write(f"{line}\n")
    
    conn.close()
    
    # Get file size
    file_size = os.path.getsize('database_export.sql')
    print(f"✅ Exported to database_export.sql ({file_size:,} bytes)")
    
    return 'database_export.sql'

def create_base64_database():
    """Create base64 encoded database for API transfer"""
    print("🔄 Creating base64 encoded database...")
    
    with open('stock_forecast.db', 'rb') as f:
        db_data = f.read()
    
    # Encode to base64
    b64_data = base64.b64encode(db_data).decode('utf-8')
    
    with open('database_b64.txt', 'w') as f:
        f.write(b64_data)
    
    print(f"✅ Created database_b64.txt ({len(b64_data):,} characters)")
    return 'database_b64.txt'

def get_database_stats():
    """Get database statistics"""
    conn = sqlite3.connect('stock_forecast.db')
    cursor = conn.cursor()
    
    # Get table counts
    tables = ['orders', 'products', 'sales']
    stats = {}
    
    for table in tables:
        try:
            cursor.execute(f'SELECT COUNT(*) FROM {table}')
            count = cursor.fetchone()[0]
            stats[table] = count
        except sqlite3.OperationalError:
            stats[table] = 0
    
    # Get date range
    try:
        cursor.execute('SELECT MIN(booking_date), MAX(booking_date) FROM orders')
        date_range = cursor.fetchone()
        stats['date_range'] = date_range
    except:
        stats['date_range'] = (None, None)
    
    conn.close()
    return stats

def main():
    print("🚀 Database Transfer Preparation")
    print("=" * 50)
    
    # Check if database exists
    if not os.path.exists('stock_forecast.db'):
        print("❌ stock_forecast.db not found!")
        return
    
    # Get database stats
    stats = get_database_stats()
    print(f"📊 Database Statistics:")
    for table, count in stats.items():
        if table != 'date_range':
            print(f"  📦 {table}: {count:,} records")
    
    if stats['date_range'][0]:
        print(f"  📅 Date Range: {stats['date_range'][0]} to {stats['date_range'][1]}")
    
    # Create exports
    sql_file = export_database_to_sql()
    b64_file = create_base64_database()
    
    print("\n🎯 Transfer Options:")
    print(f"1. SQL Export: {sql_file}")
    print(f"2. Base64 File: {b64_file}")
    print(f"3. Direct File: stock_forecast.db")
    
    print("\n📋 Next Steps:")
    print("1. Deploy your code to Render")
    print("2. Upload database using one of these methods:")
    print("   - Method A: Use Render file manager to upload stock_forecast.db to /data/db/")
    print("   - Method B: Use database_export.sql with import API endpoint")
    print("   - Method C: Use database_b64.txt for API transfer")
    
    print(f"\n✅ Ready for production deployment!")

if __name__ == '__main__':
    main()
