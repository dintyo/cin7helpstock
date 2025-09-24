"""
Rate-Limited Sync Manager - Based on example app's proven patterns
Handles Cin7's 60 calls/minute limit properly
"""
import sqlite3
import requests
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import os
import json
from dotenv import load_dotenv

# Load environment variables FIRST
load_dotenv()

logger = logging.getLogger(__name__)

class RateLimitedCin7Sync:
    """
    Handles Cin7 API syncing with proper rate limiting
    Based on example app patterns: 60 calls/minute = ~1 call per second
    """
    
    def __init__(self, db_path: str = 'stock_forecast.db'):
        self.db_path = db_path
        self.account_id = os.environ.get('CIN7_ACCOUNT_ID')
        self.api_key = os.environ.get('CIN7_API_KEY')
        self.base_url = os.environ.get('CIN7_BASE_URL', 'https://inventory.dearsystems.com/ExternalApi/v2')
        
        if not self.account_id or not self.api_key:
            raise ValueError("Missing CIN7_ACCOUNT_ID or CIN7_API_KEY")
        
        # Rate limiting settings (from example app)
        self.last_request_time = 0
        self.min_interval = 1.2  # 1.2 seconds between requests (50 calls/minute, under 60 limit)
        self.detail_interval = 1.8  # 1.8 seconds between order detail calls (33 calls/minute)
        
        self.init_tables()
    
    def init_tables(self):
        """Initialize database tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Products table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY,
                sku TEXT UNIQUE NOT NULL,
                description TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Orders table with reference_id for idempotency
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
        
        # Sync state tracking
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sync_state (
                id INTEGER PRIMARY KEY,
                sync_type TEXT UNIQUE NOT NULL,
                last_sync_timestamp TEXT,
                last_sync_success BOOLEAN DEFAULT TRUE,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def _wait_for_rate_limit(self, detail_call: bool = False):
        """Enforce rate limiting based on example app patterns"""
        current_time = time.time()
        elapsed = current_time - self.last_request_time
        
        required_interval = self.detail_interval if detail_call else self.min_interval
        
        if elapsed < required_interval:
            sleep_time = required_interval - elapsed
            logger.info(f"⏱️  Rate limiting: waiting {sleep_time:.1f}s")
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def _make_request(self, endpoint: str, params: Dict = None, is_detail_call: bool = False) -> Dict:
        """Make rate-limited API request"""
        self._wait_for_rate_limit(detail_call=is_detail_call)
        
        headers = {
            'api-auth-accountid': self.account_id,
            'api-auth-applicationkey': self.api_key,
            'Content-Type': 'application/json'
        }
        
        url = f"{self.base_url}{endpoint}"
        
        try:
            logger.info(f"🌐 API call: {endpoint}")
            response = requests.get(url, headers=headers, params=params, timeout=30)
            
            # Handle rate limiting (from example app)
            if response.status_code == 429:
                retry_after = int(response.headers.get('Retry-After', 60))
                logger.warning(f"🚫 Rate limited! Waiting {retry_after} seconds...")
                time.sleep(retry_after)
                return self._make_request(endpoint, params, is_detail_call)
            
            if response.status_code == 503:
                logger.warning("🚫 Service unavailable! Waiting 10 seconds...")
                time.sleep(10)
                return self._make_request(endpoint, params, is_detail_call)
            
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            logger.error(f"❌ API request failed for {endpoint}: {e}")
            raise
    
    def sync_date_window(self, start_date: str, end_date: str, 
                        max_orders: int = 50, dry_run: bool = True) -> Dict:
        """
        Sync orders for a specific date window
        
        Args:
            start_date: YYYY-MM-DD format
            end_date: YYYY-MM-DD format  
            max_orders: Limit for testing
            dry_run: If True, don't actually insert data
        """
        try:
            logger.info(f"🔄 {'DRY RUN: ' if dry_run else ''}Syncing orders from {start_date} to {end_date}")
            
            # Fetch orders for date range
            params = {
                'Page': 1,
                'Limit': 100,
                'OrderDateFrom': start_date,
                'OrderDateTo': end_date
            }
            
            result = self._make_request('/SaleList', params)
            orders = result.get('SaleList', [])
            
            logger.info(f"📊 Found {len(orders)} orders in date range")
            
            # Limit for testing
            if max_orders:
                orders = orders[:max_orders]
                logger.info(f"🔬 Limited to {len(orders)} orders for testing")
            
            # Process orders
            stats = {
                'total_found': len(result.get('SaleList', [])),
                'processed': 0,
                'inserted': 0,
                'skipped': 0,
                'voided': 0,
                'lines_inserted': 0
            }
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get existing SKUs
            cursor.execute('SELECT sku FROM products')
            existing_skus = {row[0] for row in cursor.fetchall()}
            
            for i, order in enumerate(orders):
                stats['processed'] += 1
                
                # Skip voided orders
                if order.get('Status', '').upper() == 'VOIDED':
                    stats['voided'] += 1
                    logger.info(f"⏭️  Skipped voided order: {order.get('OrderNumber')}")
                    continue
                
                order_number = order.get('OrderNumber', '')
                sale_id = order.get('SaleID', '')
                
                if not order_number or not sale_id:
                    stats['skipped'] += 1
                    continue
                
                logger.info(f"📦 Processing {i+1}/{len(orders)}: {order_number}")
                
                # Get order detail (this is the expensive call)
                try:
                    order_detail = self._make_request('/Sale', {'ID': sale_id}, is_detail_call=True)
                except Exception as e:
                    logger.error(f"❌ Failed to get detail for {order_number}: {e}")
                    stats['skipped'] += 1
                    continue
                
                # Extract order lines
                lines = self._extract_order_lines(order, order_detail)
                
                if not lines:
                    stats['skipped'] += 1
                    continue
                
                # Store lines
                lines_stored = 0
                for line in lines:
                    if self._store_order_line(cursor, line, existing_skus, dry_run):
                        lines_stored += 1
                        stats['lines_inserted'] += 1
                
                if lines_stored > 0:
                    stats['inserted'] += 1
                else:
                    stats['skipped'] += 1
                
                if not dry_run:
                    conn.commit()
                
                # Progress update
                logger.info(f"   ✅ Stored {lines_stored} lines from {order_number}")
            
            conn.close()
            
            return {
                'success': True,
                'period': f"{start_date} to {end_date}",
                'dry_run': dry_run,
                'stats': stats,
                'message': f"{'DRY RUN: ' if dry_run else ''}Processed {stats['processed']} orders, {stats['lines_inserted']} lines stored"
            }
            
        except Exception as e:
            logger.error(f"❌ Sync failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _extract_order_lines(self, order: Dict, order_detail: Dict) -> List[Dict]:
        """Extract line items from order detail"""
        lines = []
        
        # Get basic order info
        order_number = order.get('OrderNumber', '')
        order_date = order.get('OrderDate', '').split('T')[0]
        
        # Extract lines from order detail
        order_data = order_detail.get('Order', {})
        line_items = order_data.get('Lines', [])
        
        for line in line_items:
            sku = line.get('SKU', '').strip()
            quantity = line.get('Quantity', 0)
            description = line.get('Name', '')
            
            if sku and quantity > 0:
                # Map warehouse (simplified for MVP)
                warehouse = self._map_warehouse(order_detail)
                
                lines.append({
                    'order_number': order_number,
                    'sku': sku,
                    'description': description,
                    'quantity': quantity,
                    'warehouse': warehouse,
                    'booking_date': order_date,
                    'reference_id': f"{order.get('SaleID')}:{sku}"
                })
        
        return lines
    
    def _map_warehouse(self, order_detail: Dict) -> str:
        """Map Cin7 location to warehouse (based on example app)"""
        # Look for pick locations in fulfilments
        fulfilments = order_detail.get('Fulfilments', [])
        
        for fulfilment in fulfilments:
            pick_lines = fulfilment.get('Pick', {}).get('Lines', [])
            for line in pick_lines:
                location = line.get('Location', '')
                if 'CNTVIC' in location:
                    return 'VIC'
                elif 'WCLQLD' in location:
                    return 'QLD'
        
        # Fallback to order location
        order_location = order_detail.get('Location', '')
        if 'VIC' in order_location:
            return 'VIC'
        elif 'QLD' in order_location:
            return 'QLD'
        
        return 'NSW'  # Default
    
    def _store_order_line(self, cursor, line: Dict, existing_skus: set, dry_run: bool) -> bool:
        """Store individual order line with idempotency"""
        try:
            sku = line['sku']
            reference_id = line['reference_id']
            
            # Check if already exists (idempotency)
            cursor.execute('SELECT id FROM orders WHERE reference_id = ?', (reference_id,))
            if cursor.fetchone():
                return False  # Already exists
            
            if not dry_run:
                # Add SKU if not exists
                if sku not in existing_skus:
                    cursor.execute('''
                        INSERT OR IGNORE INTO products (sku, description)
                        VALUES (?, ?)
                    ''', (sku, line['description']))
                    existing_skus.add(sku)
                
                # Insert order line
                cursor.execute('''
                    INSERT INTO orders 
                    (order_number, sku, quantity, warehouse, booking_date, reference_id)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    line['order_number'],
                    line['sku'],
                    line['quantity'],
                    line['warehouse'],
                    line['booking_date'],
                    line['reference_id']
                ))
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to store line: {e}")
            return False
    
    def estimate_sync_time(self, start_date: str, end_date: str) -> Dict:
        """Estimate how long a sync would take"""
        try:
            # Get order count for date range (just first page to estimate)
            params = {
                'Page': 1,
                'Limit': 100,
                'OrderDateFrom': start_date,
                'OrderDateTo': end_date
            }
            
            result = self._make_request('/SaleList', params)
            orders = result.get('SaleList', [])
            total_estimate = len(orders) * 10  # Rough estimate based on pagination
            
            # Time estimation
            # Each order needs 1 list call + 1 detail call = 2 calls
            # At 1.8s per detail call + 1.2s per list call = ~3s per order
            estimated_seconds = total_estimate * 3
            estimated_minutes = estimated_seconds / 60
            
            return {
                'success': True,
                'date_range': f"{start_date} to {end_date}",
                'estimated_orders': total_estimate,
                'estimated_time': {
                    'seconds': estimated_seconds,
                    'minutes': round(estimated_minutes, 1),
                    'hours': round(estimated_minutes / 60, 1)
                },
                'rate_limit_info': {
                    'calls_per_minute': 33,  # Conservative estimate
                    'detail_call_interval': self.detail_interval,
                    'list_call_interval': self.min_interval
                },
                'recommendation': 'Start with 1-7 days for testing' if estimated_minutes > 30 else 'Safe to proceed'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

# Create Flask app with rate-limited sync
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

sync_manager = RateLimitedCin7Sync()

@app.route('/health')
def health():
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

@app.route('/sync/estimate')
def estimate_sync():
    """Estimate sync time for a date range"""
    start_date = request.args.get('start', '2025-01-01')
    end_date = request.args.get('end', '2025-09-24')
    
    estimate = sync_manager.estimate_sync_time(start_date, end_date)
    return jsonify(estimate)

@app.route('/sync/window')
def sync_window():
    """Sync a specific date window with proper rate limiting"""
    start_date = request.args.get('start', '2025-09-17')  # Default last week
    end_date = request.args.get('end', '2025-09-24')
    max_orders = int(request.args.get('max', 10))  # Limit for testing
    dry_run = request.args.get('apply') != 'true'
    
    result = sync_manager.sync_date_window(start_date, end_date, max_orders, dry_run)
    return jsonify(result)

@app.route('/velocity/<sku>')
def calculate_velocity(sku):
    """Calculate velocity with flexible date range"""
    try:
        # Allow custom date range instead of just "days back"
        start_date = request.args.get('start')
        end_date = request.args.get('end') 
        days_back = int(request.args.get('days', 30))
        
        conn = sqlite3.connect('stock_forecast.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Build date filter
        if start_date and end_date:
            date_filter = 'AND booking_date BETWEEN ? AND ?'
            date_params = [start_date, end_date]
            period_desc = f"{start_date} to {end_date}"
        else:
            date_filter = 'AND booking_date >= date("now", "-{} days")'.format(days_back)
            date_params = []
            period_desc = f"last {days_back} days"
        
        query_sql = f'''
            SELECT 
                SUM(quantity) as total_quantity,
                COUNT(*) as order_count,
                MIN(booking_date) as first_sale,
                MAX(booking_date) as last_sale
            FROM orders 
            WHERE sku = ? 
            {date_filter}
        '''
        
        cursor.execute(query_sql, [sku] + date_params)
        result = cursor.fetchone()
        
        if not result or not result['total_quantity']:
            return jsonify({
                'sku': sku,
                'period': period_desc,
                'daily_velocity': 0,
                'message': 'No sales data found in period'
            })
        
        total_qty = result['total_quantity']
        
        # Calculate actual days between first and last sale
        if result['first_sale'] and result['last_sale']:
            first_date = datetime.strptime(result['first_sale'], '%Y-%m-%d')
            last_date = datetime.strptime(result['last_sale'], '%Y-%m-%d')
            actual_days = (last_date - first_date).days + 1
        else:
            actual_days = 1
        
        # Use actual days for velocity, not query period
        daily_velocity = total_qty / actual_days
        
        # Get product info
        cursor.execute('SELECT description FROM products WHERE sku = ?', (sku,))
        product = cursor.fetchone()
        
        conn.close()
        
        return jsonify({
            'sku': sku,
            'description': product['description'] if product else '',
            'period': period_desc,
            'actual_sales_days': actual_days,
            'total_quantity_sold': total_qty,
            'order_count': result['order_count'],
            'daily_velocity': round(daily_velocity, 2),
            'weekly_velocity': round(daily_velocity * 7, 2),
            'monthly_velocity': round(daily_velocity * 30, 2),
            'first_sale': result['first_sale'],
            'last_sale': result['last_sale'],
            'note': f"Velocity based on {actual_days} actual sales days, not query period"
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    print("🚀 Rate-Limited Stock Sync App")
    print("📊 Proper rate limiting: 33-50 calls/minute")
    print("🌐 Server: http://localhost:5000")
    print("\n📋 Test Endpoints:")
    print("  GET  /sync/estimate?start=2025-01-01&end=2025-09-24 - Estimate sync time")
    print("  GET  /sync/window?start=2025-09-17&end=2025-09-24&max=5&apply=false - Sync window (dry run)")
    print("  GET  /velocity/OBQ?start=2024-06-04&end=2024-06-04 - Velocity for specific period")
    print("  GET  /velocity/OBQ - Velocity for last 30 days")
    
    app.run(debug=True, port=5001)  # Different port to avoid conflicts
