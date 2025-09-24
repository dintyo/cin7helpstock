"""
Real Stock Integration - Connect to Cin7 ProductAvailability API
"""
import requests
import time
import logging
from typing import Dict, List, Optional
import os
from dotenv import load_dotenv
import sqlite3

load_dotenv()
logger = logging.getLogger(__name__)

class Cin7StockClient:
    """Client for fetching real stock levels from Cin7"""
    
    def __init__(self):
        self.account_id = os.environ.get('CIN7_ACCOUNT_ID')
        self.api_key = os.environ.get('CIN7_API_KEY')
        self.base_url = os.environ.get('CIN7_BASE_URL', 'https://inventory.dearsystems.com/ExternalApi/v2')
        
        if not self.account_id or not self.api_key:
            raise ValueError("Missing CIN7_ACCOUNT_ID or CIN7_API_KEY")
        
        self.last_request_time = 0
        self.min_interval = 1.5  # Rate limiting
    
    def _wait_for_rate_limit(self):
        """Enforce rate limiting"""
        current_time = time.time()
        elapsed = current_time - self.last_request_time
        
        if elapsed < self.min_interval:
            sleep_time = self.min_interval - elapsed
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def _make_request(self, endpoint: str, params: Dict = None) -> Dict:
        """Make rate-limited API request"""
        self._wait_for_rate_limit()
        
        headers = {
            'api-auth-accountid': self.account_id,
            'api-auth-applicationkey': self.api_key,
            'Content-Type': 'application/json'
        }
        
        url = f"{self.base_url}{endpoint}"
        
        try:
            logger.info(f"🌐 Fetching stock: {endpoint}")
            response = requests.get(url, headers=headers, params=params, timeout=30)
            
            if response.status_code == 429:
                retry_after = int(response.headers.get('Retry-After', 60))
                logger.warning(f"🚫 Rate limited! Waiting {retry_after}s...")
                time.sleep(retry_after)
                return self._make_request(endpoint, params)
            
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            logger.error(f"❌ Stock API request failed: {e}")
            raise
    
    def fetch_product_availability(self, page: int = 1, limit: int = 1000) -> List[Dict]:
        """Fetch current stock levels from Cin7 ProductAvailability API"""
        try:
            params = {
                'Page': page,
                'Limit': limit
            }
            
            result = self._make_request('/ProductAvailability', params)
            
            # Handle different response formats
            if isinstance(result, list):
                availability_data = result
            else:
                availability_data = result.get('ProductAvailabilityList', [])
            
            # Transform to our format
            stock_data = []
            for item in availability_data:
                # Map location to warehouse
                location = item.get('Location', '')
                warehouse = self._map_location_to_warehouse(location)
                
                if warehouse:  # Only include target warehouses
                    stock_data.append({
                        'sku': item.get('SKU', ''),
                        'description': item.get('Name', ''),
                        'location': location,
                        'warehouse': warehouse,
                        'on_hand': float(item.get('OnHand', 0)),
                        'available': float(item.get('Available', 0)),
                        'allocated': float(item.get('Allocated', 0)),
                        'on_order': float(item.get('OnOrder', 0)),
                        'in_transit': float(item.get('InTransit', 0))
                    })
            
            logger.info(f"✅ Fetched {len(stock_data)} stock records from {len(availability_data)} total")
            return stock_data
            
        except Exception as e:
            logger.error(f"❌ Failed to fetch stock availability: {e}")
            return []
    
    def _map_location_to_warehouse(self, location: str) -> Optional[str]:
        """Map Cin7 location to warehouse code"""
        if not location:
            return None
        
        location_upper = location.upper()
        
        if 'CNTVIC' in location_upper or 'VIC' in location_upper:
            return 'VIC'
        elif 'WCLQLD' in location_upper or 'QLD' in location_upper:
            return 'QLD'
        elif 'NSW' in location_upper or 'MAIN' in location_upper:
            return 'NSW'
        
        return None  # Skip unknown locations
    
    def fetch_all_stock_levels(self) -> Dict[str, Dict[str, float]]:
        """Fetch all stock levels and organize by SKU and warehouse"""
        all_stock_data = []
        page = 1
        
        # Fetch all pages
        while page <= 10:  # Safety limit
            stock_data = self.fetch_product_availability(page=page)
            
            if not stock_data:
                break
            
            all_stock_data.extend(stock_data)
            
            # If we got less than 1000 records, we're done
            if len(stock_data) < 1000:
                break
            
            page += 1
        
        # Organize by SKU and warehouse
        stock_by_sku = {}
        
        for item in all_stock_data:
            sku = item['sku']
            warehouse = item['warehouse']
            
            if sku not in stock_by_sku:
                stock_by_sku[sku] = {}
            
            stock_by_sku[sku][warehouse] = {
                'on_hand': item['on_hand'],
                'available': item['available'],
                'allocated': item['allocated'],
                'location': item['location']
            }
        
        return stock_by_sku

def update_stock_database(stock_data: Dict):
    """Update local database with real stock levels"""
    conn = sqlite3.connect('stock_forecast.db')
    cursor = conn.cursor()
    
    # Create stock levels table if not exists
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS stock_levels (
            id INTEGER PRIMARY KEY,
            sku TEXT NOT NULL,
            warehouse TEXT NOT NULL,
            on_hand REAL NOT NULL,
            available REAL NOT NULL,
            allocated REAL NOT NULL,
            location TEXT,
            last_updated TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(sku, warehouse)
        )
    ''')
    
    updated_count = 0
    
    for sku, warehouses in stock_data.items():
        for warehouse, levels in warehouses.items():
            try:
                cursor.execute('''
                    INSERT OR REPLACE INTO stock_levels 
                    (sku, warehouse, on_hand, available, allocated, location, last_updated)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    sku,
                    warehouse,
                    levels['on_hand'],
                    levels['available'],
                    levels['allocated'],
                    levels['location'],
                    time.strftime('%Y-%m-%d %H:%M:%S')
                ))
                updated_count += 1
                
            except Exception as e:
                logger.error(f"Failed to update stock for {sku}/{warehouse}: {e}")
    
    conn.commit()
    conn.close()
    
    logger.info(f"✅ Updated {updated_count} stock level records")
    return updated_count

# Test function
def test_stock_integration():
    """Test the stock integration"""
    print("🧪 Testing Cin7 Stock Integration...")
    
    try:
        client = Cin7StockClient()
        
        # Test single page first
        print("📊 Fetching first page of stock data...")
        stock_data = client.fetch_product_availability(page=1, limit=10)
        
        print(f"✅ Found {len(stock_data)} stock records")
        
        # Show sample data
        for item in stock_data[:3]:
            print(f"   📦 {item['sku']}: {item['on_hand']} on hand at {item['warehouse']}")
        
        if stock_data:
            # Test database update
            print("\n💾 Testing database update...")
            sample_data = {item['sku']: {item['warehouse']: {
                'on_hand': item['on_hand'],
                'available': item['available'],
                'allocated': item['allocated'],
                'location': item['location']
            }} for item in stock_data}
            
            count = update_stock_database(sample_data)
            print(f"✅ Updated {count} stock records in database")
        
        return True
        
    except Exception as e:
        print(f"❌ Stock integration test failed: {e}")
        return False

if __name__ == '__main__':
    test_stock_integration()
