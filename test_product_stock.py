"""
Test if Product endpoint includes stock information
"""
import requests
import os
import time
import json
from dotenv import load_dotenv

load_dotenv()

def test_product_for_stock():
    """Test Product endpoint for stock data"""
    account_id = os.environ.get('CIN7_ACCOUNT_ID')
    api_key = os.environ.get('CIN7_API_KEY')
    base_url = os.environ.get('CIN7_BASE_URL', 'https://inventory.dearsystems.com/ExternalApi/v2')
    
    headers = {
        'api-auth-accountid': account_id,
        'api-auth-applicationkey': api_key,
        'Content-Type': 'application/json'
    }
    
    try:
        print("🧪 Testing Product endpoint for stock data...")
        
        params = {'Page': 1, 'Limit': 3}
        response = requests.get(f"{base_url}/Product", 
                              headers=headers, 
                              params=params, 
                              timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            products = data.get('Products', [])
            
            print(f"✅ Found {len(products)} products")
            
            if products:
                sample = products[0]
                print(f"\n📦 Sample product keys:")
                for key in sorted(sample.keys()):
                    value = sample[key]
                    print(f"   {key}: {value}")
                
                # Look for stock-related fields
                stock_fields = [k for k in sample.keys() if any(word in k.lower() for word in ['stock', 'quantity', 'available', 'hand'])]
                if stock_fields:
                    print(f"\n📊 Stock-related fields found: {stock_fields}")
                else:
                    print(f"\n❌ No stock fields found in Product endpoint")
                    print(f"   Available fields: {list(sample.keys())}")
        
        else:
            print(f"❌ Error: {response.status_code}")
            print(response.text[:200])
            
    except Exception as e:
        print(f"❌ Test failed: {e}")

if __name__ == '__main__':
    test_product_for_stock()
