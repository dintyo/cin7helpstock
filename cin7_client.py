"""
Cin7 Core (DEAR) API Client
Based on the example app's API integration
"""
import requests
import time
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class Cin7Client:
    """Client for interacting with Cin7 Core (DEAR) API"""
    
    def __init__(self, account_id: str, api_key: str, base_url: str):
        self.account_id = account_id
        self.api_key = api_key
        self.base_url = base_url
        self.session = requests.Session()
        self._setup_session()
        
        # Warehouse location mappings (from example app)
        self.warehouse_mappings = {
            'CNTVIC': 'VIC',
            'WCLQLD': 'QLD',
            'Main Warehouse': 'NSW',
            # Add more mappings as needed
        }
    
    def _setup_session(self):
        """Setup session with authentication headers"""
        self.session.headers.update({
            'api-auth-accountid': self.account_id,
            'api-auth-applicationkey': self.api_key,
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
    
    def _make_request(self, endpoint: str, params: Optional[Dict] = None, 
                     method: str = 'GET', retry_count: int = 3) -> Dict:
        """Make API request with retry logic"""
        url = f"{self.base_url}{endpoint}"
        
        for attempt in range(retry_count):
            try:
                if method == 'GET':
                    response = self.session.get(url, params=params, timeout=30)
                else:
                    response = self.session.post(url, json=params, timeout=30)
                
                # Handle rate limiting
                if response.status_code == 429:
                    retry_after = int(response.headers.get('Retry-After', 5))
                    logger.warning(f"Rate limited. Waiting {retry_after} seconds...")
                    time.sleep(retry_after)
                    continue
                
                response.raise_for_status()
                return response.json()
                
            except requests.exceptions.Timeout:
                logger.warning(f"Timeout on attempt {attempt + 1}")
                if attempt < retry_count - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue
                raise
                
            except requests.exceptions.RequestException as e:
                logger.error(f"Request failed: {e}")
                if attempt < retry_count - 1:
                    time.sleep(2 ** attempt)
                    continue
                raise
        
        raise Exception(f"Failed after {retry_count} attempts")
    
    def fetch_locations(self) -> List[Dict]:
        """Fetch all warehouse locations"""
        try:
            result = self._make_request('/ref/location', {'Page': 1, 'Limit': 200})
            return result.get('LocationList', [])
        except Exception as e:
            logger.error(f"Failed to fetch locations: {e}")
            return []
    
    def fetch_orders(self, order_date_from: str = None, order_date_to: str = None,
                    updated_since: str = None, page: int = 1, limit: int = 100) -> List[Dict]:
        """Fetch orders from Cin7"""
        all_orders = []
        
        while True:
            params = {
                'Page': page,
                'Limit': limit
            }
            
            # Add date filters
            if order_date_from:
                params['OrderDateFrom'] = order_date_from
            if order_date_to:
                params['OrderDateTo'] = order_date_to
            if updated_since:
                params['CreatedSince'] = updated_since
                # Also send these for compatibility
                params['LastModifiedOnFrom'] = updated_since
                params['UpdatedFrom'] = updated_since
            
            try:
                result = self._make_request('/SaleList', params)
                sales = result.get('SaleList', [])
                
                if not sales:
                    break
                
                # Filter out cancelled orders (VOIDED status)
                valid_sales = [s for s in sales if s.get('Status') != 'VOIDED']
                
                # Enrich with warehouse information
                for sale in valid_sales:
                    # Map OrderLocationID to warehouse code if needed
                    sale['warehouse_code'] = self._map_location_to_warehouse(
                        sale.get('OrderLocationID')
                    )
                
                all_orders.extend(valid_sales)
                
                # Check if there are more pages
                if len(sales) < limit:
                    break
                    
                page += 1
                time.sleep(1)  # Rate limiting delay
                
            except Exception as e:
                logger.error(f"Failed to fetch orders page {page}: {e}")
                break
        
        return all_orders
    
    def fetch_order_detail(self, sale_id: str) -> Optional[Dict]:
        """Fetch detailed information for a specific order"""
        try:
            result = self._make_request(f'/Sale', {'ID': sale_id})
            return result
        except Exception as e:
            logger.error(f"Failed to fetch order detail for {sale_id}: {e}")
            return None
    
    def fetch_products(self, page: int = 1, limit: int = 100, 
                      updated_since: str = None) -> List[Dict]:
        """Fetch products/SKUs from Cin7"""
        all_products = []
        
        while True:
            params = {
                'Page': page,
                'Limit': limit
            }
            
            if updated_since:
                params['UpdatedSince'] = updated_since
            
            try:
                result = self._make_request('/Products', params)
                products = result.get('Products', [])
                
                if not products:
                    break
                
                # Transform to consistent format
                for product in products:
                    all_products.append({
                        'sku': product.get('ProductCode', ''),
                        'description': product.get('Name', ''),
                        'length': product.get('Length', 0),
                        'width': product.get('Width', 0),
                        'height': product.get('Height', 0),
                        'weight': product.get('Weight', 0),
                        'barcode': product.get('Barcode', ''),
                        # Calculate CBM (cubic meters)
                        'cbm': self._calculate_cbm(
                            product.get('Length'),
                            product.get('Width'),
                            product.get('Height')
                        )
                    })
                
                if len(products) < limit:
                    break
                    
                page += 1
                time.sleep(1)  # Rate limiting
                
            except Exception as e:
                logger.error(f"Failed to fetch products page {page}: {e}")
                break
        
        return all_products
    
    def sync_recent_orders(self, created_since: str, max_orders: int = 500) -> Dict:
        """Sync recent orders using CreatedSince (the working date filter)"""
        logger.info(f"🔄 Starting recent orders sync since {created_since}")
        
        try:
            conn = sqlite3.connect(DATABASE)
            cursor = conn.cursor()
            
            # Track results
            orders_found = 0
            lines_stored = 0
            
            # Fetch orders using CreatedSince
            page = 1
            total_fetched = 0
            
            while page <= 20 and total_fetched < max_orders:  # Safety limits
                params = {
                    'Page': page,
                    'Limit': min(1000, max_orders - total_fetched),
                    'CreatedSince': created_since
                }
                
                logger.info(f"📋 Fetching page {page} with CreatedSince...")
                
                result = self._make_request('/SaleList', params)
                orders = result.get('SaleList', [])
                
                if not orders:
                    logger.info(f"📄 Page {page}: No more orders")
                    break
                
                orders_found += len(orders)
                total_fetched += len(orders)
                
                logger.info(f"📄 Page {page}: {len(orders)} orders")
                
                # Process each order
                for order in orders:
                    if order.get('Status', '').upper() == 'VOIDED':
                        continue
                    
                    # Get order detail to extract line items
                    sale_id = order.get('SaleID')
                    if not sale_id:
                        continue
                    
                    try:
                        detail = self._make_request('/Sale', {'ID': sale_id})
                        
                        # Extract lines using same logic as sync_date_window
                        pick_lines = []
                        fulfilments = detail.get('Fulfilments', [])
                        
                        for fulfilment in fulfilments:
                            pick_data = fulfilment.get('Pick', {})
                            if pick_data.get('Lines'):
                                for line in pick_data['Lines']:
                                    pick_lines.append({
                                        'sku': line.get('SKU', '').strip(),
                                        'quantity': line.get('Quantity', 0),
                                        'location': line.get('Location', ''),
                                        'description': line.get('Name', '')
                                    })
                        
                        # Fallback to order lines
                        order_lines = []
                        order_data = detail.get('Order', {})
                        if order_data.get('Lines'):
                            for line in order_data['Lines']:
                                order_lines.append({
                                    'sku': line.get('SKU', '').strip(),
                                    'quantity': line.get('Quantity', 0),
                                    'location': None,
                                    'description': line.get('Name', '')
                                })
                        
                        # Use pick lines if available, otherwise order lines
                        lines_to_process = pick_lines if pick_lines else order_lines
                        
                        for line in lines_to_process:
                            sku = line['sku']
                            quantity = line['quantity']
                            description = line['description']
                            location = line['location']
                            
                            if not sku or quantity <= 0:
                                continue
                            
                            # Map warehouse from location
                            warehouse = 'NSW'  # Default
                            if location:
                                if 'CNTVIC' in location or 'VIC' in location:
                                    warehouse = 'VIC'
                                elif 'WCLQLD' in location or 'QLD' in location:
                                    warehouse = 'QLD'
                            
                            reference_id = f"{sale_id}:{sku}"
                            
                            # Check if exists
                            cursor.execute('SELECT id FROM orders WHERE reference_id = ?', (reference_id,))
                            if cursor.fetchone():
                                continue
                            
                            # Add product if needed
                            cursor.execute('INSERT OR IGNORE INTO products (sku, description) VALUES (?, ?)',
                                        (sku, description))
                            
                            # Add order
                            cursor.execute('''
                                INSERT INTO orders
                                (order_number, sku, quantity, warehouse, booking_date, reference_id)
                                VALUES (?, ?, ?, ?, ?, ?)
                            ''', (
                                order.get('OrderNumber', ''),
                                sku,
                                quantity,
                                warehouse,
                                order.get('OrderDate', '').split('T')[0],
                                reference_id
                            ))
                            
                            lines_stored += 1
                        
                        # Rate limiting
                        time.sleep(1.8)
                        
                    except Exception as e:
                        logger.error(f"Error processing order {sale_id}: {e}")
                        continue
                
                if len(orders) < 1000:
                    break
                
                page += 1
                time.sleep(1.2)  # Rate limiting between pages
            
            conn.commit()
            conn.close()
            
            logger.info(f"✅ Recent sync complete: {lines_stored} lines from {orders_found} orders")
            
            return {
                'success': True,
                'orders_found': orders_found,
                'lines_stored': lines_stored,
                'created_since': created_since,
                'method': 'CreatedSince'
            }
            
        except Exception as e:
            logger.error(f"Recent sync failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def fetch_stock_on_hand(self) -> List[Dict]:
        """Fetch current stock levels"""
        try:
            # Fetch stock availability
            result = self._make_request('/StockAvailability', {
                'Page': 1,
                'Limit': 1000
            })
            
            stock_list = result.get('StockAvailabilityList', [])
            
            # Transform and group by location
            stock_data = []
            for item in stock_list:
                # Each item may have multiple location stocks
                for location in item.get('AvailabilityByLocation', []):
                    stock_data.append({
                        'sku': item.get('SKU', ''),
                        'description': item.get('Name', ''),
                        'location': location.get('Location', ''),
                        'warehouse': self._map_location_to_warehouse(location.get('LocationID')),
                        'available': location.get('Available', 0),
                        'on_hand': location.get('OnHand', 0),
                        'allocated': location.get('Allocated', 0)
                    })
            
            return stock_data
            
        except Exception as e:
            logger.error(f"Failed to fetch stock on hand: {e}")
            return []
    
    def fetch_purchases(self, updated_since: str = None, page: int = 1, 
                       limit: int = 100) -> List[Dict]:
        """Fetch purchase orders (arrivals)"""
        all_purchases = []
        
        while True:
            params = {
                'Page': page,
                'Limit': limit
            }
            
            if updated_since:
                params['UpdatedSince'] = updated_since
            
            try:
                result = self._make_request('/PurchaseList', params)
                purchases = result.get('PurchaseList', [])
                
                if not purchases:
                    break
                
                all_purchases.extend(purchases)
                
                if len(purchases) < limit:
                    break
                    
                page += 1
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"Failed to fetch purchases page {page}: {e}")
                break
        
        return all_purchases
    
    def _map_location_to_warehouse(self, location_id: str) -> str:
        """Map location ID to warehouse code (VIC/QLD/NSW)"""
        # This would need to be enhanced with actual location lookup
        # For now, using simple mapping
        if not location_id:
            return 'UNKNOWN'
        
        # You might want to cache location lookups
        # For MVP, return a default
        return 'NSW'  # Default warehouse
    
    def _calculate_cbm(self, length: float, width: float, height: float) -> float:
        """Calculate cubic meters from dimensions (assuming mm input)"""
        if not all([length, width, height]):
            return 0.0
        
        # Convert mm to meters and calculate volume
        try:
            return (float(length) * float(width) * float(height)) / 1_000_000_000
        except (TypeError, ValueError):
            return 0.0
