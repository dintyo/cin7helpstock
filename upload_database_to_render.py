#!/usr/bin/env python3
"""
ONE-TIME SCRIPT: Upload local database to Render
Run this ONCE on Render, then delete it
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
        return False
    
    target_db = '/data/db/stock_forecast.db'
    
    # Check if database exists and back it up
    if os.path.exists(target_db):
        backup_path = f'/data/db/stock_forecast_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db'
        print(f"\n📦 Backing up existing database to:")
        print(f"   {backup_path}")
        shutil.copy2(target_db, backup_path)
        print("   ✅ Backup created")
    
    # Read the base64 encoded database
    print(f"\n📥 Reading encoded database from database_b64_new.txt...")
    try:
        with open('database_b64_new.txt', 'r') as f:
            encoded_data = f.read()
        
        print(f"   ✅ Read {len(encoded_data)} characters")
    except Exception as e:
        print(f"   ❌ Error reading file: {e}")
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
        
        cursor.execute("SELECT COUNT(*) FROM orders")
        order_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT MIN(booking_date), MAX(booking_date) FROM orders")
        date_range = cursor.fetchone()
        
        conn.close()
        
        print(f"   ✅ Database verified!")
        print(f"   📊 Total orders: {order_count}")
        print(f"   📅 Date range: {date_range[0]} to {date_range[1]}")
        
    except Exception as e:
        print(f"   ⚠️  Warning: Couldn't verify database: {e}")
    
    print("\n" + "=" * 80)
    print("✅ DATABASE UPLOAD COMPLETE!")
    print("=" * 80)
    print("\nYour Render app now has the full database with all historical data.")
    print("\n⚠️  IMPORTANT: Delete this script after use!")
    print("   - Remove: upload_database_to_render.py")
    print("   - Remove: database_b64_new.txt")
    print("=" * 80)
    
    return True


if __name__ == '__main__':
    # Safety check - don't run locally
    if not os.path.exists('/data/db'):
        print("\n⚠️  WARNING: This script should ONLY be run on Render!")
        print("It will not work on your local machine.")
        print("\nTo upload to Render:")
        print("1. git add upload_database_to_render.py database_b64_new.txt")
        print("2. git commit -m 'Add database upload script'")
        print("3. git push")
        print("4. In Render Shell, run: python upload_database_to_render.py")
        print("5. After success, delete these files and push again")
    else:
        success = upload_database()
        exit(0 if success else 1)

