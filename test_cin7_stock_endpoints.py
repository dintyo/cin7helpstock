"""
Test different Cin7 endpoints to find current stock levels
"""
import requests
import os
from dotenv import load_dotenv
import json
import time

load_dotenv()

def test_cin7_stock_endpoints():
    account_id = os.environ.get('CIN7_ACCOUNT_ID')
    api_key = os.environ.get('CIN7_API_KEY')
    base_url = os.environ.get('CIN7_BASE_URL', 'https://inventory.dearsystems.com/ExternalApi/v2')
    
    if not account_id or not api_key:
        print("❌ Missing CIN7_ACCOUNT_ID or CIN7_API_KEY")
        return
    
    headers = {
        'api-auth-accountid': account_id,
        'api-auth-applicationkey': api_key,
        'Content-Type': 'application/json'
    }
    
    # Test different endpoints that might have stock information
    endpoints_to_test = [
        {
            'name': 'Product (basic product info)',
            'url': '/Product',
            'params': {'Page': 1, 'Limit': 5}
        },
        {
            'name': 'ProductAvailability (stock levels)',
            'url': '/ProductAvailability', 
            'params': {'Page': 1, 'Limit': 5}
        },
        {
            'name': 'Product with SKU filter',
            'url': '/Product',
            'params': {'Page': 1, 'Limit': 10, 'sku': 'OB-ESS'}
        },
        {
            'name': 'ProductAvailability with SKU filter',
            'url': '/ProductAvailability',
            'params': {'Page': 1, 'Limit': 10, 'sku': 'OB-ESS'}
        }
    ]
    
    for endpoint in endpoints_to_test:
        print(f"\n🔍 Testing {endpoint['name']}...")
        print(f"📍 URL: {base_url}{endpoint['url']}")
        print(f"📊 Params: {endpoint['params']}")
        
        try:
            response = requests.get(f"{base_url}{endpoint['url']}", headers=headers, params=endpoint['params'])
            print(f"📊 Status: {response.status_code}")
            print(f"📊 Content-Type: {response.headers.get('Content-Type', 'unknown')}")
            print(f"📊 Response length: {len(response.text)} chars")
            
            if response.status_code == 200:
                content_type = response.headers.get('Content-Type', '')
                
                if 'application/json' in content_type:
                    try:
                        data = response.json()
                        print(f"✅ Valid JSON response")
                        
                        if isinstance(data, dict):
                            print(f"📦 Response keys: {list(data.keys())}")
                            
                            # Look for product data
                            products = []
                            if 'Products' in data:
                                products = data['Products']
                                print(f"📋 Found {len(products)} products in 'Products' key")
                            elif 'ProductList' in data:
                                products = data['ProductList']
                                print(f"📋 Found {len(products)} products in 'ProductList' key")
                            elif 'ProductAvailabilityList' in data:
                                products = data['ProductAvailabilityList']
                                print(f"📋 Found {len(products)} products in 'ProductAvailabilityList' key")
                            
                            if products and len(products) > 0:
                                print(f"\n📝 Sample product structure:")
                                sample = products[0]
                                print(json.dumps(sample, indent=2)[:800] + "...")
                                
                                # Look for OB-ESS or OB-ORG items
                                ob_products = [p for p in products if 
                                             str(p.get('SKU', '')).startswith('OB-ESS-') or 
                                             str(p.get('SKU', '')).startswith('OB-ORG-')]
                                
                                if ob_products:
                                    print(f"\n🎯 Found {len(ob_products)} OB-ESS/OB-ORG products:")
                                    for product in ob_products:
                                        sku = product.get('SKU', '')
                                        # Look for stock-related fields
                                        stock_fields = {}
                                        for key in ['OnHand', 'Available', 'StockOnHand', 'Quantity', 'Stock']:
                                            if key in product:
                                                stock_fields[key] = product[key]
                                        
                                        print(f"   📦 {sku}: {stock_fields}")
                                else:
                                    print(f"🔍 No OB-ESS/OB-ORG products found in sample")
                            else:
                                print("❌ No products found in response")
                        
                        elif isinstance(data, list):
                            print(f"📋 Response is array with {len(data)} items")
                            if data:
                                print(f"📝 Sample item: {json.dumps(data[0], indent=2)[:500]}...")
                        
                    except json.JSONDecodeError as e:
                        print(f"❌ JSON decode error: {e}")
                        print(f"📄 Raw response (first 300 chars): {response.text[:300]}")
                
                elif 'text/html' in content_type:
                    print("❌ Got HTML response (likely 404/error page)")
                    if "Page not found" in response.text:
                        print("🚫 Endpoint does not exist")
                    
                else:
                    print(f"❓ Unknown content type: {content_type}")
                    print(f"📄 Response preview: {response.text[:200]}")
            
            else:
                print(f"❌ HTTP Error {response.status_code}")
                print(f"📄 Error response: {response.text[:300]}")
        
        except Exception as e:
            print(f"❌ Request failed: {e}")
        
        # Rate limiting
        time.sleep(2)

if __name__ == "__main__":
    test_cin7_stock_endpoints()
