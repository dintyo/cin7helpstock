"""
Test script to validate Cin7 API connection and data access
Run this first to ensure everything is working
"""
import os
import requests
from dotenv import load_dotenv
from datetime import datetime, timedelta

load_dotenv()

def test_cin7_connection():
    """Test basic Cin7 API connectivity"""
    account_id = os.environ.get('CIN7_ACCOUNT_ID')
    api_key = os.environ.get('CIN7_API_KEY')
    base_url = os.environ.get('CIN7_BASE_URL', 'https://inventory.dearsystems.com/ExternalApi/v2')
    
    if not account_id or not api_key:
        print("❌ Missing CIN7_ACCOUNT_ID or CIN7_API_KEY in .env file")
        return False
    
    print(f"🔑 Using Account ID: {account_id[:8]}...")
    print(f"🔑 Using API Key: {api_key[:8]}...")
    print(f"🌐 Base URL: {base_url}")
    
    headers = {
        'api-auth-accountid': account_id,
        'api-auth-applicationkey': api_key,
        'Content-Type': 'application/json'
    }
    
    # Test 1: Basic connectivity
    print("\n📡 Testing basic API connectivity...")
    try:
        response = requests.get(f"{base_url}/SaleList", 
                              headers=headers, 
                              params={'Page': 1, 'Limit': 1},
                              timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            sale_count = len(data.get('SaleList', []))
            print(f"✅ API Connected! Found {sale_count} orders on first page")
        else:
            print(f"❌ API Error: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False
    
    # Test 2: Recent orders with details
    print("\n📊 Testing recent orders...")
    try:
        from_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        
        response = requests.get(f"{base_url}/SaleList", 
                              headers=headers,
                              params={
                                  'Page': 1, 
                                  'Limit': 5,
                                  'OrderDateFrom': from_date
                              },
                              timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            orders = data.get('SaleList', [])
            print(f"✅ Found {len(orders)} orders in last 7 days")
            
            # Test getting order detail
            if orders:
                first_order = orders[0]
                print(f"📋 Testing order detail for: {first_order.get('OrderNumber')}")
                
                detail_response = requests.get(f"{base_url}/Sale",
                                             headers=headers,
                                             params={'ID': first_order.get('SaleID')},
                                             timeout=30)
                
                if detail_response.status_code == 200:
                    detail = detail_response.json()
                    lines = detail.get('Order', {}).get('Lines', [])
                    print(f"✅ Order has {len(lines)} line items")
                    
                    if lines:
                        sample_line = lines[0]
                        print(f"📦 Sample item: {sample_line.get('SKU')} - Qty: {sample_line.get('Quantity')}")
                else:
                    print(f"❌ Failed to get order detail: {detail_response.status_code}")
        
    except Exception as e:
        print(f"❌ Order test failed: {e}")
        return False
    
    # Test 3: Products
    print("\n🏷️  Testing products API...")
    try:
        response = requests.get(f"{base_url}/Product",
                              headers=headers,
                              params={'Page': 1, 'Limit': 3},
                              timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            products = data.get('Products', [])
            print(f"✅ Found {len(products)} products on first page")
            
            if products:
                sample = products[0]
                print(f"📦 Sample product: {sample.get('ProductCode')} - {sample.get('Name')}")
        else:
            print(f"❌ Products API error: {response.status_code}")
    
    except Exception as e:
        print(f"❌ Products test failed: {e}")
    
    print("\n🎉 Cin7 connection tests completed!")
    return True

if __name__ == '__main__':
    print("🧪 Testing Cin7 API Connection")
    print("=" * 50)
    
    success = test_cin7_connection()
    
    if success:
        print("\n✅ All tests passed! You can now run the Flask app:")
        print("   python simple_app.py")
        print("\nThen test these endpoints:")
        print("   curl http://localhost:5000/test-cin7")
        print("   curl http://localhost:5000/sync-sales")
        print("   curl http://localhost:5000/stock-status")
    else:
        print("\n❌ Tests failed. Check your .env file and Cin7 credentials.")
