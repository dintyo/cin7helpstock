"""
Test different Cin7 stock endpoints to find the right one
"""
import requests
import os
import time
from dotenv import load_dotenv

load_dotenv()

def test_stock_endpoints():
    """Test various stock-related endpoints"""
    account_id = os.environ.get('CIN7_ACCOUNT_ID')
    api_key = os.environ.get('CIN7_API_KEY')
    base_url = os.environ.get('CIN7_BASE_URL', 'https://inventory.dearsystems.com/ExternalApi/v2')
    
    headers = {
        'api-auth-accountid': account_id,
        'api-auth-applicationkey': api_key,
        'Content-Type': 'application/json'
    }
    
    # Test different stock endpoints
    endpoints_to_test = [
        '/ProductAvailability',
        '/Product',  # Products might include stock info
        '/ProductAvailabilityList',
        '/Stock',
        '/Inventory',
        '/StockAvailability'
    ]
    
    for endpoint in endpoints_to_test:
        try:
            print(f"\n🧪 Testing: {endpoint}")
            
            params = {'Page': 1, 'Limit': 1}
            response = requests.get(f"{base_url}{endpoint}", 
                                  headers=headers, 
                                  params=params, 
                                  timeout=10)
            
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    print(f"   ✅ SUCCESS! Response type: {type(data)}")
                    
                    if isinstance(data, dict):
                        keys = list(data.keys())[:5]
                        print(f"   Keys: {keys}")
                        
                        # Look for stock-related data
                        for key in data:
                            if 'availability' in key.lower() or 'stock' in key.lower() or 'product' in key.lower():
                                sample = data[key]
                                if isinstance(sample, list) and sample:
                                    sample_item = sample[0]
                                    print(f"   Sample {key}: {list(sample_item.keys())[:8]}")
                    
                    elif isinstance(data, list) and data:
                        sample = data[0]
                        print(f"   Sample item keys: {list(sample.keys())[:8]}")
                        
                except Exception as e:
                    print(f"   Response not JSON: {e}")
                    print(f"   First 200 chars: {response.text[:200]}")
            
            elif response.status_code == 404:
                print(f"   ❌ Not found")
            else:
                print(f"   ❌ Error: {response.status_code} - {response.text[:100]}")
                
        except Exception as e:
            print(f"   ❌ Request failed: {e}")
        
        time.sleep(1)  # Rate limiting

if __name__ == '__main__':
    test_stock_endpoints()
