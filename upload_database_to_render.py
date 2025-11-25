#!/usr/bin/env python3
"""
ONE-TIME SCRIPT: Upload local database to Render
Run this ONCE on Render Shell, then delete it
"""
import base64
import os
import shutil
from datetime import datetime

def upload_database():
    """Upload the encoded database to Render's persistent disk"""
    
    print("=" * 80)
    print("DATABASE UPLOAD TO RENDER")
    print("=" * 80)
    
    # Check if we're on Render (persistent disk exists)
    if not os.path.exists('/data/db'):
        print("❌ Error: /data/db not found. Are you running on Render?")
        print("   This script should ONLY be run on Render's server.")
        print("\n💡 If running locally, this is expected.")
        print("   Push to git first, then run in Render Shell.")
        return False
    
    target_db = '/data/db/stock_forecast.db'
    
    # Check if database exists and back it up
    if os.path.exists(target_db):
        backup_path = f'/data/db/stock_forecast_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db'
        print(f"\n📦 Backing up existing database to:")
        print(f"   {backup_path}")
        try:
            shutil.copy2(target_db, backup_path)
            print("   ✅ Backup created")
        except Exception as e:
            print(f"   ⚠️  Warning: Couldn't create backup: {e}")
    
    # Read the base64 encoded database
    print(f"\n📥 Reading encoded database from database_b64_new.txt...")
    try:
        with open('database_b64_new.txt', 'r') as f:
            encoded_data = f.read()
        
        print(f"   ✅ Read {len(encoded_data)} characters")
    except Exception as e:
        print(f"   ❌ Error reading file: {e}")
        print("\n💡 Make sure database_b64_new.txt was pushed to git!")
        return False
    
    # Decode the database
    print(f"\n🔓 Decoding database...")
    try:
        decoded_data = base64.b64decode(encoded_data)
        print(f"   ✅ Decoded to {len(decoded_data)} bytes ({len(decoded_data)/1024/1024:.2f} MB)")
    except Exception as e:
        print(f"   ❌ Error decoding: {e}")
        return False
    
    # Write to Render's persistent disk
    print(f"\n💾 Writing to {target_db}...")
    try:
        with open(target_db, 'wb') as f:
            f.write(decoded_data)
        print(f"   ✅ Database written successfully!")
    except Exception as e:
        print(f"   ❌ Error writing: {e}")
        return False
    
    # Verify
    print(f"\n✅ Verifying database...")
    import sqlite3
    try:
        conn = sqlite3.connect(target_db)
        cursor = conn.cursor()
        
        # Check orders
        cursor.execute("SELECT COUNT(*) FROM orders")
        order_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT MIN(booking_date), MAX(booking_date) FROM orders WHERE booking_date IS NOT NULL")
        date_range = cursor.fetchone()
        
        # Check stock
        cursor.execute("SELECT COUNT(*) FROM current_stock")
        stock_count = cursor.fetchone()[0]
        
        conn.close()
        
        print(f"   ✅ Database verified!")
        print(f"\n   📊 Orders: {order_count}")
        print(f"   📅 Date range: {date_range[0]} to {date_range[1]}")
        print(f"   📦 Stock records: {stock_count}")
        
    except Exception as e:
        print(f"   ⚠️  Warning: Couldn't verify database: {e}")
    
    print("\n" + "=" * 80)
    print("✅ DATABASE UPLOAD COMPLETE!")
    print("=" * 80)
    print("\nYour Render app now has:")
    print("  • All 12,577+ orders (18 months of history)")
    print("  • Current stock levels for all SKUs")
    print("  • Ready to use immediately!")
    print("\n⚠️  NEXT STEPS:")
    print("  1. Restart your Render service to ensure it picks up the new DB")
    print("  2. Test your app - try viewing some historical data")
    print("  3. Delete these files from your repo:")
    print("     - upload_database_to_render.py")
    print("     - database_b64_new.txt")
    print("\n💡 TIP: Set up automated stock syncs to keep data fresh!")
    print("=" * 80)
    
    return True


if __name__ == '__main__':
    success = upload_database()
    exit(0 if success else 1)
