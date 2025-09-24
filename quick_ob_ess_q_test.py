"""
FAST test for OB-ESS-Q - Start with just 1 week of data
"""
import requests
import os
import time
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

def quick_test_ob_ess_q():
    """Quick test with just 1 week of data"""
    account_id = os.environ.get('CIN7_ACCOUNT_ID')
    api_key = os.environ.get('CIN7_API_KEY')
    base_url = os.environ.get('CIN7_BASE_URL', 'https://inventory.dearsystems.com/ExternalApi/v2')
    
    headers = {
        'api-auth-accountid': account_id,
        'api-auth-applicationkey': api_key,
        'Content-Type': 'application/json'
    }
    
    # Start with just 1 week for testing
    start_date = '2025-06-11'
    end_date = '2025-06-18'  # Just 1 week
    
    print(f"🔍 QUICK TEST: OB-ESS-Q in customer sales orders")
    print(f"📅 Testing period: {start_date} to {end_date} (1 week)")
    print("=" * 50)
    
    try:
        # Step 1: Get sales list with MAX page size
        print("📋 Getting customer sales orders (max page size)...")
        
        params = {
            'Page': 1,
            'Limit': 1000,  # Use maximum page size
            'OrderDateFrom': start_date,
            'OrderDateTo': end_date
        }
        
        response = requests.get(f"{base_url}/SaleList", headers=headers, params=params, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        orders = data.get('SaleList', [])
        
        print(f"   ✅ Found {len(orders)} orders in 1 week")
        
        if not orders:
            print("❌ No orders found - trying different date range")
            return test_known_period()
        
        # Show sample to verify we have real data
        if orders:
            sample = orders[0]
            print(f"   📋 Sample: {sample.get('OrderNumber')} - {sample.get('OrderDate')[:10]} - {sample.get('Status')}")
        
        # Step 2: Check ONLY first 5 orders for speed
        print(f"\n📦 Quick check: Testing first 5 orders only...")
        
        ob_ess_q_found = []
        
        for i, order in enumerate(orders[:5]):  # ONLY first 5 for speed
            sale_id = order.get('SaleID')
            order_number = order.get('OrderNumber')
            order_date = order.get('OrderDate', '')[:10]
            
            print(f"   🔍 Checking {i+1}/5: {order_number}...")
            
            # Skip voided
            if order.get('Status', '').upper() == 'VOIDED':
                print(f"      ⏭️ Skipped (VOIDED)")
                continue
            
            try:
                # Get order detail
                detail_response = requests.get(f"{base_url}/Sale", 
                                             headers=headers, 
                                             params={'ID': sale_id}, 
                                             timeout=30)
                detail_response.raise_for_status()
                detail = detail_response.json()
                
                # Check order lines
                order_data = detail.get('Order', {})
                if order_data.get('Lines'):
                    for line in order_data['Lines']:
                        sku = line.get('SKU', '').strip()
                        if sku == 'OB-ESS-Q':
                            qty = line.get('Quantity', 0)
                            ob_ess_q_found.append({
                                'order': order_number,
                                'date': order_date,
                                'qty': qty
                            })
                            print(f"      🎯 FOUND OB-ESS-Q: {qty} units!")
                        else:
                            print(f"      📦 Found SKU: {sku}")
                
                time.sleep(1.2)  # Rate limiting
                
            except Exception as e:
                print(f"      ❌ Error: {e}")
        
        print(f"\n🎯 QUICK TEST RESULTS:")
        print(f"   📊 Orders checked: 5/{len(orders)}")
        print(f"   📦 OB-ESS-Q orders found: {len(ob_ess_q_found)}")
        
        if ob_ess_q_found:
            total_qty = sum(item['qty'] for item in ob_ess_q_found)
            print(f"   📈 Total OB-ESS-Q: {total_qty} units")
            for item in ob_ess_q_found:
                print(f"      {item['order']} - {item['date']} - {item['qty']} units")
        else:
            print("   ❌ No OB-ESS-Q found in first 5 orders")
            print("   💡 Try expanding to more orders or different date range")
        
        return len(ob_ess_q_found), sum(item['qty'] for item in ob_ess_q_found) if ob_ess_q_found else 0
        
    except Exception as e:
        print(f"❌ Quick test failed: {e}")
        return 0, 0

def test_known_period():
    """Test with a known period that has data"""
    print(f"\n🔄 Trying known period with data (June 2024)...")
    
    account_id = os.environ.get('CIN7_ACCOUNT_ID')
    api_key = os.environ.get('CIN7_API_KEY')
    base_url = os.environ.get('CIN7_BASE_URL', 'https://inventory.dearsystems.com/ExternalApi/v2')
    
    headers = {
        'api-auth-accountid': account_id,
        'api-auth-applicationkey': api_key,
        'Content-Type': 'application/json'
    }
    
    # Try June 2024 (we know has data)
    params = {
        'Page': 1,
        'Limit': 10,
        'OrderDateFrom': '2024-06-01',
        'OrderDateTo': '2024-06-30'
    }
    
    try:
        response = requests.get(f"{base_url}/SaleList", headers=headers, params=params, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        orders = data.get('SaleList', [])
        
        print(f"   ✅ Found {len(orders)} orders in June 2024")
        
        if orders:
            for i, order in enumerate(orders[:3]):
                print(f"   {i+1}. {order.get('OrderNumber')} - {order.get('OrderDate')[:10]} - {order.get('Status')}")
        
        return len(orders), 0
        
    except Exception as e:
        print(f"   ❌ Known period test failed: {e}")
        return 0, 0

if __name__ == '__main__':
    print("⚡ QUICK OB-ESS-Q Test (Fast Version)")
    print("🎯 Goal: Find OB-ESS-Q quickly with minimal API calls")
    print()
    
    orders_found, qty_found = quick_test_ob_ess_q()
    
    print(f"\n" + "=" * 50)
    print(f"⚡ QUICK RESULTS:")
    print(f"   Orders with OB-ESS-Q: {orders_found}")
    print(f"   Total OB-ESS-Q units: {qty_found}")
    print(f"   ⏱️ Time saved: ~90% (5 detail calls vs 100+)")
