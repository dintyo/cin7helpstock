#!/usr/bin/env python3
"""
Daily Sync Script - Keeps database current with Cin7
Syncs both stock levels and recent orders
Run this once per day (ideally at night)
"""
import sys
import os
import sqlite3
from datetime import datetime, timedelta
from dotenv import load_dotenv
from unified_stock_app import UnifiedCin7Client
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('daily_sync.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

load_dotenv()

def get_db_path():
    """Get the correct database path (local or Render)"""
    db_path = os.environ.get('DATABASE_PATH', 'stock_forecast.db')
    
    # Check for Render persistent disk
    if db_path == 'stock_forecast.db' and os.path.exists('/data/db'):
        db_path = '/data/db/stock_forecast.db'
    
    return db_path

def sync_stock_levels():
    """Sync current stock levels from Cin7"""
    logger.info("=" * 80)
    logger.info("STEP 1: SYNCING STOCK LEVELS")
    logger.info("=" * 80)
    
    try:
        client = UnifiedCin7Client()
        
        # Fetch stock data
        result = client.sync_stock_from_cin7()
        
        if not result.get('success'):
            logger.error(f"Stock fetch failed: {result.get('error')}")
            return {'success': False, 'error': result.get('error')}
        
        stock_levels = result.get('stock_levels', {})
        sku_count = result.get('sku_count', 0)
        
        logger.info(f"✅ Fetched stock for {sku_count} SKUs from Cin7")
        
        # Save to database
        db_path = get_db_path()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Clear old stock data
        cursor.execute("DELETE FROM current_stock")
        
        # Insert new stock data
        inserted = 0
        for sku, total_stock in stock_levels.items():
            if total_stock > 0:
                cursor.execute('''
                    INSERT INTO current_stock (sku, warehouse, quantity, last_updated)
                    VALUES (?, 'ALL', ?, CURRENT_TIMESTAMP)
                ''', (sku, total_stock))
                inserted += 1
        
        conn.commit()
        conn.close()
        
        total_units = sum(stock_levels.values())
        logger.info(f"✅ Stock sync complete: {inserted} SKUs, {total_units:.0f} total units")
        
        return {
            'success': True,
            'skus': inserted,
            'total_units': total_units
        }
        
    except Exception as e:
        logger.error(f"Stock sync failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {'success': False, 'error': str(e)}

def sync_recent_orders(days_back=7):
    """Sync recent orders (last N days)"""
    logger.info("=" * 80)
    logger.info(f"STEP 2: SYNCING RECENT ORDERS (LAST {days_back} DAYS)")
    logger.info("=" * 80)
    
    try:
        client = UnifiedCin7Client()
        
        # Calculate date range
        start_date = datetime.now() - timedelta(days=days_back)
        created_since = start_date.strftime('%Y-%m-%dT00:00:00Z')
        
        logger.info(f"Syncing orders since: {created_since}")
        
        # Sync orders
        result = client.sync_recent_orders(
            created_since=created_since,
            max_orders=2000  # Should be plenty for a week
        )
        
        if result.get('success'):
            orders_found = result.get('orders_found', 0)
            lines_stored = result.get('lines_stored', 0)
            
            logger.info(f"✅ Order sync complete: {orders_found} orders, {lines_stored} lines")
            
            return {
                'success': True,
                'orders': orders_found,
                'lines': lines_stored
            }
        else:
            logger.error(f"Order sync failed: {result.get('error')}")
            return {'success': False, 'error': result.get('error')}
            
    except Exception as e:
        logger.error(f"Order sync failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {'success': False, 'error': str(e)}

def get_database_stats():
    """Get current database statistics"""
    try:
        db_path = get_db_path()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Total orders
        cursor.execute("SELECT COUNT(*) FROM orders")
        total_orders = cursor.fetchone()[0]
        
        # Date range
        cursor.execute("SELECT MIN(booking_date), MAX(booking_date) FROM orders WHERE booking_date IS NOT NULL")
        date_range = cursor.fetchone()
        
        # Stock count
        cursor.execute("SELECT COUNT(*), SUM(quantity) FROM current_stock")
        stock_data = cursor.fetchone()
        
        conn.close()
        
        return {
            'total_orders': total_orders,
            'earliest_order': date_range[0],
            'latest_order': date_range[1],
            'stock_skus': stock_data[0] or 0,
            'total_stock_units': stock_data[1] or 0
        }
    except Exception as e:
        logger.error(f"Failed to get database stats: {e}")
        return {}

def main():
    """Main sync routine"""
    logger.info("\n" + "=" * 80)
    logger.info("DAILY SYNC STARTED")
    logger.info(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 80)
    
    db_path = get_db_path()
    logger.info(f"Database: {db_path}")
    
    # Get stats before sync
    logger.info("\n📊 Database Stats (Before Sync):")
    before_stats = get_database_stats()
    if before_stats:
        logger.info(f"   Orders: {before_stats.get('total_orders', 0)}")
        logger.info(f"   Date Range: {before_stats.get('earliest_order')} to {before_stats.get('latest_order')}")
        logger.info(f"   Stock: {before_stats.get('stock_skus', 0)} SKUs, {before_stats.get('total_stock_units', 0):.0f} units")
    
    # Track results
    results = {
        'stock_sync': None,
        'order_sync': None
    }
    
    # Step 1: Sync stock levels
    logger.info("")
    results['stock_sync'] = sync_stock_levels()
    
    # Step 2: Sync recent orders
    logger.info("")
    results['order_sync'] = sync_recent_orders(days_back=7)
    
    # Get stats after sync
    logger.info("\n📊 Database Stats (After Sync):")
    after_stats = get_database_stats()
    if after_stats:
        logger.info(f"   Orders: {after_stats.get('total_orders', 0)}")
        logger.info(f"   Date Range: {after_stats.get('earliest_order')} to {after_stats.get('latest_order')}")
        logger.info(f"   Stock: {after_stats.get('stock_skus', 0)} SKUs, {after_stats.get('total_stock_units', 0):.0f} units")
        
        # Calculate changes
        if before_stats:
            new_orders = after_stats.get('total_orders', 0) - before_stats.get('total_orders', 0)
            if new_orders > 0:
                logger.info(f"\n   📈 Added {new_orders} new orders")
    
    # Summary
    logger.info("\n" + "=" * 80)
    logger.info("DAILY SYNC SUMMARY")
    logger.info("=" * 80)
    
    stock_success = results['stock_sync'].get('success', False) if results['stock_sync'] else False
    order_success = results['order_sync'].get('success', False) if results['order_sync'] else False
    
    if stock_success:
        logger.info(f"✅ Stock Sync: {results['stock_sync'].get('skus', 0)} SKUs")
    else:
        logger.error(f"❌ Stock Sync: Failed - {results['stock_sync'].get('error', 'Unknown')}")
    
    if order_success:
        logger.info(f"✅ Order Sync: {results['order_sync'].get('orders', 0)} orders, {results['order_sync'].get('lines', 0)} lines")
    else:
        logger.error(f"❌ Order Sync: Failed - {results['order_sync'].get('error', 'Unknown')}")
    
    logger.info("\n" + "=" * 80)
    
    if stock_success and order_success:
        logger.info("✅ DAILY SYNC COMPLETED SUCCESSFULLY")
        logger.info("=" * 80)
        return 0
    else:
        logger.error("⚠️  DAILY SYNC COMPLETED WITH ERRORS")
        logger.error("=" * 80)
        return 1

if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
