"""
Test if there are actually orders in August 2025
"""
import requests
import os
from dotenv import load_dotenv

load_dotenv()

def test_august_orders():
    """Check if orders exist in August 2025"""
    account_id = os.environ.get('CIN7_ACCOUNT_ID')
    api_key = os.environ.get('CIN7_API_KEY')
    base_url = os.environ.get('CIN7_BASE_URL', 'https://inventory.dearsystems.com/ExternalApi/v2')
    
    headers = {
        'api-auth-accountid': account_id,
        'api-auth-applicationkey': api_key,
        'Content-Type': 'application/json'
    }
    
    # Test different date ranges
    date_ranges = [
        ('2025-08-01', '2025-08-31', 'August 2025'),
        ('2025-07-01', '2025-07-31', 'July 2025'),
        ('2025-06-01', '2025-06-30', 'June 2025'),
        ('2025-01-01', '2025-03-31', 'Q1 2025'),
        ('2024-06-01', '2024-06-30', 'June 2024 (known data)')
    ]
    
    for start_date, end_date, period_name in date_ranges:
        try:
            print(f"\n🔍 Testing {period_name} ({start_date} to {end_date})")
            
            params = {
                'Page': 1,
                'Limit': 10,
                'OrderDateFrom': start_date,
                'OrderDateTo': end_date
            }
            
            response = requests.get(f"{base_url}/SaleList", headers=headers, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            orders = data.get('SaleList', [])
            
            print(f"   📊 Found {len(orders)} orders")
            
            if orders:
                # Show sample orders
                for i, order in enumerate(orders[:3]):
                    status = order.get('Status', 'UNKNOWN')
                    print(f"   {i+1}. {order.get('OrderNumber')} - {order.get('OrderDate')[:10]} - {status}")
            
            import time
            time.sleep(1)  # Rate limiting
            
        except Exception as e:
            print(f"   ❌ Error: {e}")

if __name__ == '__main__':
    test_august_orders()
