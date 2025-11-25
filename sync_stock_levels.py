#!/usr/bin/env python3
"""
Sync Current Stock Levels from Cin7
Fetches on-hand quantities and saves to database
"""
import sqlite3
import os
from datetime import datetime
from dotenv import load_dotenv
from unified_stock_app import UnifiedCin7Client

load_dotenv()

def sync_stock_levels():
    """Sync current stock levels from Cin7 and save to database"""
    print("=" * 80)
    print("SYNCING STOCK LEVELS FROM CIN7")
    print("=" * 80)
    
    print("\n📊 This will fetch current on-hand quantities")
    print("\n⏱️  This takes 2-3 minutes...\n")
    
    try:
        client = UnifiedCin7Client()
        
        # Fetch stock data from Cin7
        result = client.sync_stock_from_cin7()
        
        if not result.get('success'):
            print(f"\n❌ Stock fetch failed: {result.get('error', 'Unknown error')}")
            return False
        
        stock_levels = result.get('stock_levels', {})
        sku_count = result.get('sku_count', 0)
        
        print(f"\n✅ Fetched stock for {sku_count} SKUs from Cin7")
        
        # Now save to database
        db_path = os.environ.get('DATABASE_PATH', 'stock_forecast.db')
        if db_path == 'stock_forecast.db' and os.path.exists('/data/db'):
            db_path = '/data/db/stock_forecast.db'
        
        print(f"\n💾 Saving to database: {db_path}")
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Clear old stock data
        cursor.execute("DELETE FROM current_stock")
        
        # Insert new stock data
        # Table structure: id, sku, warehouse, quantity, last_updated
        inserted = 0
        for sku, total_stock in stock_levels.items():
            if total_stock > 0:
                # Store as aggregate (no specific warehouse in this sync method)
                cursor.execute('''
                    INSERT INTO current_stock (sku, warehouse, quantity, last_updated)
                    VALUES (?, 'ALL', ?, CURRENT_TIMESTAMP)
                ''', (sku, total_stock))
                inserted += 1
        
        conn.commit()
        conn.close()
        
        print(f"   ✅ Saved {inserted} SKUs to database")
        
        # Show summary
        total_units = sum(stock_levels.values())
        
        print(f"\n📈 Summary:")
        print(f"   Total SKUs: {sku_count}")
        print(f"   Total units: {total_units:.0f}")
        
        # Show some examples
        print(f"\n📦 Sample Stock Levels:")
        for i, (sku, stock) in enumerate(list(stock_levels.items())[:10]):
            if stock > 0:
                print(f"   {sku}: {stock:.0f} units")
        
        print("\n" + "=" * 80)
        print("✅ STOCK LEVELS SYNCED SUCCESSFULLY")
        print("=" * 80)
        print("\nYour app now has current inventory quantities!")
        print("\n💡 TIP: Stock levels change constantly.")
        print("   Run this daily to keep quantities up to date.")
        print("=" * 80)
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error during stock sync: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    import sys
    success = sync_stock_levels()
    sys.exit(0 if success else 1)

