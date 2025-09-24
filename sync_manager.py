"""
Sync Manager - Based on example app's proven sync patterns
Handles incremental syncing with state tracking
"""
import sqlite3
import requests
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import os

logger = logging.getLogger(__name__)

class SyncManager:
    """Manages incremental syncing with Cin7 API"""
    
    def __init__(self, db_path: str = 'stock_forecast.db'):
        self.db_path = db_path
        self.account_id = os.environ.get('CIN7_ACCOUNT_ID')
        self.api_key = os.environ.get('CIN7_API_KEY')
        self.base_url = os.environ.get('CIN7_BASE_URL', 'https://inventory.dearsystems.com/ExternalApi/v2')
        
        if not self.account_id or not self.api_key:
            raise ValueError("Missing CIN7_ACCOUNT_ID or CIN7_API_KEY")
        
        self.init_sync_tables()
    
    def init_sync_tables(self):
        """Initialize sync state and core tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Sync state table (like example app)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sync_state (
                id INTEGER PRIMARY KEY,
                sync_type TEXT UNIQUE NOT NULL,
                last_sync_timestamp TEXT,
                last_sync_success BOOLEAN DEFAULT TRUE,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Products table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY,
                sku TEXT UNIQUE NOT NULL,
                description TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Orders table with reference_id for idempotency (like example app)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY,
                order_number TEXT NOT NULL,
                sku TEXT NOT NULL,
                quantity REAL NOT NULL,
                warehouse TEXT NOT NULL,
                booking_date TEXT NOT NULL,
                reference_id TEXT UNIQUE NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Warehouses lookup
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS warehouses (
                id INTEGER PRIMARY KEY,
                code TEXT UNIQUE NOT NULL,
                name TEXT,
                region TEXT
            )
        ''')
        
        # Initialize default warehouses
        cursor.execute('INSERT OR IGNORE INTO warehouses (code, name, region) VALUES (?, ?, ?)', 
                      ('VIC', 'Victoria Warehouse', 'VIC'))
        cursor.execute('INSERT OR IGNORE INTO warehouses (code, name, region) VALUES (?, ?, ?)', 
                      ('QLD', 'Queensland Warehouse', 'QLD'))
        cursor.execute('INSERT OR IGNORE INTO warehouses (code, name, region) VALUES (?, ?, ?)', 
                      ('NSW', 'New South Wales Warehouse', 'NSW'))
        
        # Initialize sync state
        cursor.execute('''
            INSERT OR IGNORE INTO sync_state (sync_type, last_sync_timestamp) 
            VALUES (?, ?)
        ''', ('cin7_orders', (datetime.now() - timedelta(days=7)).isoformat()))
        
        conn.commit()
        conn.close()
    
    def _make_request(self, endpoint: str, params: Dict = None) -> Dict:
        """Make API request with proper headers and rate limiting"""
        headers = {
            'api-auth-accountid': self.account_id,
            'api-auth-applicationkey': self.api_key,
            'Content-Type': 'application/json'
        }
        
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=30)
            
            if response.status_code == 429:
                logger.warning("Rate limited - waiting 60 seconds...")
                time.sleep(60)
                return self._make_request(endpoint, params)
            
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            logger.error(f"API request failed for {endpoint}: {e}")
            raise
    
    def get_last_sync_time(self, sync_type: str = 'cin7_orders') -> datetime:
        """Get last successful sync timestamp"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            'SELECT last_sync_timestamp FROM sync_state WHERE sync_type = ?',
            (sync_type,)
        )
        
        result = cursor.fetchone()
        conn.close()
        
        if result and result[0]:
            return datetime.fromisoformat(result[0])
        else:
            # Default to 7 days ago
            return datetime.now() - timedelta(days=7)
    
    def update_sync_state(self, sync_type: str, timestamp: datetime, success: bool = True):
        """Update sync state timestamp"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE sync_state 
            SET last_sync_timestamp = ?, last_sync_success = ?, updated_at = ?
            WHERE sync_type = ?
        ''', (timestamp.isoformat(), success, datetime.now().isoformat(), sync_type))
        
        conn.commit()
        conn.close()
    
    def sync_recent_orders(self, max_pages: int = 5, dry_run: bool = False) -> Dict:
        """
        Incremental sync of recent orders (based on example app pattern)
        """
        try:
            sync_start = datetime.now()
            last_sync = self.get_last_sync_time()
            
            # Safety buffer (like example app) - subtract 5 minutes
            safe_last_sync = last_sync - timedelta(minutes=5)
            
            logger.info(f"🔄 Starting incremental sync from: {safe_last_sync.isoformat()}")
            
            # Preload SKUs and warehouses for performance
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT sku FROM products')
            existing_skus = {row[0] for row in cursor.fetchall()}
            
            cursor.execute('SELECT code, id FROM warehouses')
            warehouse_map = {row[0]: row[1] for row in cursor.fetchall()}
            
            total_processed = 0
            total_inserted = 0
            total_skipped = 0
            total_voided = 0
            
            # Fetch orders using updatedSince (like example app)
            for page in range(1, max_pages + 1):
                logger.info(f"📄 Fetching page {page}...")
                
                params = {
                    'Page': page,
                    'Limit': 100,  # Reasonable batch size
                    'CreatedSince': safe_last_sync.isoformat(),
                    'LastModifiedOnFrom': safe_last_sync.isoformat(),  # Compatibility
                    'UpdatedFrom': safe_last_sync.isoformat()  # Compatibility
                }
                
                try:
                    result = self._make_request('/SaleList', params)
                    orders = result.get('SaleList', [])
                    
                    if not orders:
                        logger.info(f"No more orders found on page {page}")
                        break
                    
                    logger.info(f"   Found {len(orders)} orders on page {page}")
                    
                    # Process each order
                    for order in orders:
                        total_processed += 1
                        
                        # Skip voided orders (like example app)
                        status = (order.get('Status', '')).upper()
                        if status in ['VOIDED', 'VOID', 'CANCELLED', 'CANCELED']:
                            total_voided += 1
                            continue
                        
                        # Get order detail for line items
                        order_detail = self._get_order_detail(order.get('SaleID'))
                        
                        if not order_detail:
                            continue
                        
                        # Process order lines
                        lines_processed = self._process_order_lines(
                            order, order_detail, existing_skus, warehouse_map, 
                            dry_run=dry_run
                        )
                        
                        if lines_processed > 0:
                            total_inserted += lines_processed
                        else:
                            total_skipped += 1
                        
                        # Rate limiting (like example app) - 1.8-2 seconds
                        time.sleep(1.8 + (0.4 * (page % 2)))  # Slight variation
                    
                    # Page-level rate limiting
                    if page < max_pages:
                        time.sleep(1.5)
                    
                    # Stop if we got less than full page
                    if len(orders) < 100:
                        break
                        
                except Exception as e:
                    logger.error(f"Failed to process page {page}: {e}")
                    break
            
            conn.close()
            
            # Update sync state if not dry run
            if not dry_run:
                self.update_sync_state('cin7_orders', sync_start, True)
            
            return {
                'success': True,
                'sync_period': {
                    'from': safe_last_sync.isoformat(),
                    'to': sync_start.isoformat()
                },
                'stats': {
                    'processed': total_processed,
                    'inserted': total_inserted,
                    'skipped': total_skipped,
                    'voided': total_voided
                },
                'dry_run': dry_run
            }
            
        except Exception as e:
            logger.error(f"Sync failed: {e}")
            if not dry_run:
                self.update_sync_state('cin7_orders', sync_start, False)
            
            return {
                'success': False,
                'error': str(e)
            }
    
    def _get_order_detail(self, sale_id: str) -> Optional[Dict]:
        """Get detailed order information"""
        try:
            result = self._make_request('/Sale', {'ID': sale_id})
            return result
        except Exception as e:
            logger.error(f"Failed to get order detail for {sale_id}: {e}")
            return None
    
    def _process_order_lines(self, order: Dict, order_detail: Dict, 
                           existing_skus: set, warehouse_map: Dict,
                           dry_run: bool = False) -> int:
        """Process individual order lines"""
        if not order_detail or 'Order' not in order_detail:
            return 0
        
        order_data = order_detail['Order']
        lines = order_data.get('Lines', [])
        
        if not lines:
            return 0
        
        order_number = order.get('OrderNumber', '')
        order_date = order.get('OrderDate', '').split('T')[0]
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        lines_inserted = 0
        
        try:
            for line in lines:
                sku = line.get('SKU', '').strip()
                quantity = line.get('Quantity', 0)
                description = line.get('Name', '')
                
                if not sku or quantity <= 0:
                    continue
                
                # Map warehouse (simplified for MVP)
                warehouse = self._map_warehouse_location(order_detail)
                if not warehouse:
                    continue
                
                # Create reference_id for idempotency (like example app)
                reference_id = f"{order.get('SaleID')}:{sku}"
                
                # Check if already exists
                cursor.execute('SELECT id FROM orders WHERE reference_id = ?', (reference_id,))
                if cursor.fetchone():
                    continue  # Skip duplicate
                
                if not dry_run:
                    # Add SKU if not exists
                    if sku not in existing_skus:
                        cursor.execute('''
                            INSERT OR IGNORE INTO products (sku, description)
                            VALUES (?, ?)
                        ''', (sku, description))
                        existing_skus.add(sku)
                    
                    # Insert order line
                    cursor.execute('''
                        INSERT INTO orders 
                        (order_number, sku, quantity, warehouse, booking_date, reference_id)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (order_number, sku, quantity, warehouse, order_date, reference_id))
                    
                    lines_inserted += 1
                else:
                    lines_inserted += 1  # Count for dry run
            
            conn.commit()
            return lines_inserted
            
        except Exception as e:
            logger.error(f"Failed to process order lines: {e}")
            conn.rollback()
            return 0
        finally:
            conn.close()
    
    def _map_warehouse_location(self, order_detail: Dict) -> Optional[str]:
        """Map Cin7 location to warehouse code (simplified)"""
        # Look for pick locations in fulfilments (like example app)
        fulfilments = order_detail.get('Fulfilments', [])
        
        for fulfilment in fulfilments:
            pick_lines = fulfilment.get('Pick', {}).get('Lines', [])
            for line in pick_lines:
                location = line.get('Location', '')
                if 'CNTVIC' in location or 'VIC' in location:
                    return 'VIC'
                elif 'WCLQLD' in location or 'QLD' in location:
                    return 'QLD'
        
        # Fallback to order location
        order_location = order_detail.get('Location', '')
        if 'VIC' in order_location:
            return 'VIC'
        elif 'QLD' in order_location:
            return 'QLD'
        else:
            return 'NSW'  # Default
    
    def sync_week_of_orders(self, days_back: int = 7, dry_run: bool = True) -> Dict:
        """
        Sync a specific week of orders (good for initial testing)
        """
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)
            
            logger.info(f"🔄 Syncing orders from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Preload existing data
            cursor.execute('SELECT sku FROM products')
            existing_skus = {row[0] for row in cursor.fetchall()}
            
            cursor.execute('SELECT code, id FROM warehouses')
            warehouse_map = {row[0]: row[1] for row in cursor.fetchall()}
            
            total_processed = 0
            total_inserted = 0
            total_skipped = 0
            
            # Fetch orders for date range
            params = {
                'Page': 1,
                'Limit': 50,  # Small batches for testing
                'OrderDateFrom': start_date.strftime('%Y-%m-%d'),
                'OrderDateTo': end_date.strftime('%Y-%m-%d')
            }
            
            result = self._make_request('/SaleList', params)
            orders = result.get('SaleList', [])
            
            logger.info(f"Found {len(orders)} orders in date range")
            
            # Process each order (limit for testing)
            for i, order in enumerate(orders[:10]):  # Limit to 10 for testing
                total_processed += 1
                
                logger.info(f"Processing {i+1}/{min(10, len(orders))}: {order.get('OrderNumber')}")
                
                # Skip voided
                if order.get('Status', '').upper() == 'VOIDED':
                    total_skipped += 1
                    continue
                
                # Get order detail
                order_detail = self._get_order_detail(order.get('SaleID'))
                if not order_detail:
                    total_skipped += 1
                    continue
                
                # Process lines
                lines_inserted = self._process_order_lines(
                    order, order_detail, existing_skus, warehouse_map, dry_run
                )
                
                if lines_inserted > 0:
                    total_inserted += lines_inserted
                else:
                    total_skipped += 1
                
                # Rate limiting (critical!)
                time.sleep(2.0)  # 2 second delay between orders
            
            conn.close()
            
            return {
                'success': True,
                'period': f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}",
                'stats': {
                    'found': len(orders),
                    'processed': total_processed,
                    'inserted': total_inserted,
                    'skipped': total_skipped
                },
                'dry_run': dry_run,
                'message': f"{'DRY RUN: ' if dry_run else ''}Processed {total_processed} orders, inserted {total_inserted} lines"
            }
            
        except Exception as e:
            logger.error(f"Week sync failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_sync_status(self) -> Dict:
        """Get current sync status"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get sync state
        cursor.execute('SELECT * FROM sync_state WHERE sync_type = ?', ('cin7_orders',))
        sync_state = cursor.fetchone()
        
        # Get data counts
        cursor.execute('SELECT COUNT(*) FROM products')
        product_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM orders')
        order_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(DISTINCT sku) FROM orders')
        active_skus = cursor.fetchone()[0]
        
        cursor.execute('''
            SELECT COUNT(*) FROM orders 
            WHERE booking_date >= date('now', '-7 days')
        ''')
        recent_orders = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'sync_state': {
                'last_sync': sync_state[2] if sync_state else None,
                'last_success': bool(sync_state[3]) if sync_state else None,
                'updated_at': sync_state[4] if sync_state else None
            },
            'data_counts': {
                'total_products': product_count,
                'total_orders': order_count,
                'active_skus': active_skus,
                'recent_orders_7d': recent_orders
            }
        }
