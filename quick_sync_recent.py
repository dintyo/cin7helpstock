#!/usr/bin/env python3
"""
Quick Sync - Update with recent orders (last 30 days)
Run this anytime you need to pull in the latest orders
"""
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv
from unified_stock_app import UnifiedCin7Client

load_dotenv()

def quick_sync(days_back=30):
    """Quick sync of recent orders"""
    print(f"\n🔄 Syncing last {days_back} days of orders...")
    
    start_date = datetime.now() - timedelta(days=days_back)
    created_since = start_date.strftime('%Y-%m-%dT00:00:00Z')
    
    client = UnifiedCin7Client()
    
    try:
        result = client.sync_recent_orders(
            created_since=created_since,
            max_orders=2000
        )
        
        if result.get('success'):
            print(f"✅ Success!")
            print(f"   Orders found: {result.get('orders_found', 0)}")
            print(f"   Lines stored: {result.get('lines_stored', 0)}")
            return True
        else:
            print(f"❌ Failed: {result.get('error')}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == '__main__':
    days = 30 if len(sys.argv) < 2 else int(sys.argv[1])
    quick_sync(days)

