"""
Test CORRECT date filtering for Cin7 SaleList API
Based on example app patterns
"""
import requests
import os
import time
from dotenv import load_dotenv
from datetime import datetime, timedelta

load_dotenv()

def test_correct_date_filtering():
    """Test with correct date parameter format"""
    account_id = os.environ.get('CIN7_ACCOUNT_ID')
    api_key = os.environ.get('CIN7_API_KEY')
    base_url = os.environ.get('CIN7_BASE_URL', 'https://inventory.dearsystems.com/ExternalApi/v2')
    
    headers = {
        'api-auth-accountid': account_id,
        'api-auth-applicationkey': api_key,
        'Content-Type': 'application/json'
    }
    
    print(f"🔧 Testing CORRECT date filtering")
    print(f"📅 Target: September 1-24, 2025 (should be ~400 orders)")
    print("=" * 60)
    
    # Test 1: OrderDateFrom/OrderDateTo (like example app)
    print(f"\n📋 Test 1: OrderDateFrom/OrderDateTo parameters")
    
    params1 = {
        'Page': 1,
        'Limit': 100,
        'OrderDateFrom': '2025-09-01',
        'OrderDateTo': '2025-09-24'
    }
    
    try:
        response1 = requests.get(f"{base_url}/SaleList", headers=headers, params=params1, timeout=30)
        print(f"   📡 Status: {response1.status_code}")
        
        if response1.ok:
            data1 = response1.json()
            orders1 = data1.get('SaleList', [])
            print(f"   📊 Found: {len(orders1)} orders")
            
            if orders1:
                # Check actual dates in response
                dates = [order.get('OrderDate', '')[:10] for order in orders1[:5]]
                print(f"   📅 Sample dates: {dates}")
                print(f"   📅 Date range: {min(dates)} to {max(dates)}")
        else:
            print(f"   ❌ Failed: {response1.text}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 2: CreatedSince (for recent data)
    print(f"\n📋 Test 2: CreatedSince (recent data approach)")
    
    # Calculate 30 days ago
    thirty_days_ago = datetime.now() - timedelta(days=30)
    created_since = thirty_days_ago.strftime('%Y-%m-%dT%H:%M:%SZ')
    
    params2 = {
        'Page': 1,
        'Limit': 100,
        'CreatedSince': created_since
    }
    
    try:
        response2 = requests.get(f"{base_url}/SaleList", headers=headers, params=params2, timeout=30)
        print(f"   📡 Status: {response2.status_code}")
        
        if response2.ok:
            data2 = response2.json()
            orders2 = data2.get('SaleList', [])
            print(f"   📊 Found: {len(orders2)} orders (last 30 days)")
            
            if orders2:
                # Check actual dates in response
                dates = [order.get('OrderDate', '')[:10] for order in orders2[:5]]
                print(f"   📅 Sample dates: {dates}")
                print(f"   📅 Date range: {min(dates)} to {max(dates)}")
        else:
            print(f"   ❌ Failed: {response2.text}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 3: No date filter (see total data)
    print(f"\n📋 Test 3: No date filter (total data check)")
    
    params3 = {
        'Page': 1,
        'Limit': 10  # Just a small sample
    }
    
    try:
        response3 = requests.get(f"{base_url}/SaleList", headers=headers, params=params3, timeout=30)
        print(f"   📡 Status: {response3.status_code}")
        
        if response3.ok:
            data3 = response3.json()
            orders3 = data3.get('SaleList', [])
            total_count = data3.get('Total', 'Unknown')
            
            print(f"   📊 Sample: {len(orders3)} orders")
            print(f"   📊 Total in system: {total_count}")
            
            if orders3:
                print(f"   📋 Sample orders:")
                for i, order in enumerate(orders3[:3]):
                    order_date = order.get('OrderDate', '')[:10]
                    customer = order.get('Customer', 'Unknown')
                    print(f"      {i+1}. {order.get('OrderNumber')} - {order_date} - {customer}")
        else:
            print(f"   ❌ Failed: {response3.text}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 4: Try example app's double parameter approach
    print(f"\n📋 Test 4: Double parameters (like example app)")
    
    params4 = {
        'Page': 1,
        'Limit': 50,
        'OrderDateFrom': '2025-09-01',
        'OrderDateTo': '2025-09-24',
        'DateFrom': '2025-09-01',  # Example app sends both
        'DateTo': '2025-09-24'    # Example app sends both
    }
    
    try:
        response4 = requests.get(f"{base_url}/SaleList", headers=headers, params=params4, timeout=30)
        print(f"   📡 Status: {response4.status_code}")
        
        if response4.ok:
            data4 = response4.json()
            orders4 = data4.get('SaleList', [])
            print(f"   📊 Found: {len(orders4)} orders")
            
            if orders4:
                # Check actual dates in response
                dates = [order.get('OrderDate', '')[:10] for order in orders4[:5]]
                print(f"   📅 Sample dates: {dates}")
                print(f"   📅 Date range: {min(dates)} to {max(dates)}")
        else:
            print(f"   ❌ Failed: {response4.text}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    print(f"\n" + "=" * 60)
    print(f"🎯 SUMMARY:")
    print(f"   Expected: ~400 orders for September 2025")
    print(f"   Goal: Find which parameter format works correctly")
    print(f"   Next: Use working format to find OB-ESS-Q")

if __name__ == '__main__':
    print("🔧 Cin7 Date Filtering Debug")
    print("🎯 Testing different date parameter formats")
    print("📊 Expected: ~400 orders for September (not 10,000)")
    print()
    
    test_correct_date_filtering()
