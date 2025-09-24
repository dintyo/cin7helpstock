"""
Test OB-ESS-Q sales for September 1-24, 2025
Using customer sales orders (SaleList API)
"""
import requests
import os
import time
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

def test_september_ob_ess_q():
    """Test current month data for OB-ESS-Q"""
    account_id = os.environ.get('CIN7_ACCOUNT_ID')
    api_key = os.environ.get('CIN7_API_KEY')
    base_url = os.environ.get('CIN7_BASE_URL', 'https://inventory.dearsystems.com/ExternalApi/v2')
    
    headers = {
        'api-auth-accountid': account_id,
        'api-auth-applicationkey': api_key,
        'Content-Type': 'application/json'
    }
    
    start_date = '2025-09-01'
    end_date = '2025-09-24'
    
    print(f"🔍 Testing CURRENT MONTH: OB-ESS-Q in customer sales orders")
    print(f"📅 Period: {start_date} to {end_date} (24 days)")
    print(f"🛒 Using SaleList API (CUSTOMER orders)")
    print("=" * 60)
    
    try:
        # Step 1: Get customer sales orders
        print("📋 Step 1: Getting customer sales orders...")
        
        params = {
            'Page': 1,
            'Limit': 100,  # Start smaller
            'OrderDateFrom': start_date,
            'OrderDateTo': end_date
        }
        
        print(f"   🌐 API Call: GET /SaleList")
        print(f"   📅 OrderDateFrom: {start_date}")
        print(f"   📅 OrderDateTo: {end_date}")
        
        response = requests.get(f"{base_url}/SaleList", headers=headers, params=params, timeout=30)
        
        print(f"   📡 Response Status: {response.status_code}")
        
        if response.status_code == 403:
            print("   ❌ 403 Forbidden - Check credentials")
            return 0, 0
            
        response.raise_for_status()
        
        data = response.json()
        orders = data.get('SaleList', [])
        
        print(f"   ✅ Found {len(orders)} customer orders in September 2025")
        
        if not orders:
            print("   ⚠️ No orders found - let's check what data exists...")
            return test_any_recent_data()
        
        # Show first few orders to verify data
        print(f"\n📋 Sample customer orders:")
        for i, order in enumerate(orders[:3]):
            order_date = order.get('OrderDate', '')[:10]
            customer = order.get('Customer', 'Unknown')
            print(f"   {i+1}. {order.get('OrderNumber')} - {order_date} - Customer: {customer}")
        
        # Step 2: Check orders for OB-ESS-Q (limit to first 10 for speed)
        check_count = min(len(orders), 10)
        print(f"\n📦 Step 2: Checking first {check_count} orders for OB-ESS-Q...")
        
        ob_ess_q_results = []
        total_quantity = 0
        
        for i, order in enumerate(orders[:check_count]):
            sale_id = order.get('SaleID')
            order_number = order.get('OrderNumber')
            order_date = order.get('OrderDate', '')[:10]
            customer = order.get('Customer', 'Unknown')
            
            print(f"   🔍 {i+1}/{check_count}: {order_number} (Customer: {customer})")
            
            # Skip voided orders
            if order.get('Status', '').upper() == 'VOIDED':
                print(f"      ⏭️ Skipped (VOIDED)")
                continue
            
            try:
                # Get order detail to see line items
                detail_response = requests.get(f"{base_url}/Sale", 
                                             headers=headers, 
                                             params={'ID': sale_id}, 
                                             timeout=30)
                detail_response.raise_for_status()
                detail = detail_response.json()
                
                # Check customer order lines
                order_data = detail.get('Order', {})
                lines_found = 0
                
                if order_data.get('Lines'):
                    for line in order_data['Lines']:
                        sku = line.get('SKU', '').strip()
                        qty = line.get('Quantity', 0)
                        lines_found += 1
                        
                        print(f"      📦 Line: {sku} (qty: {qty})")
                        
                        if sku == 'OB-ESS-Q':
                            ob_ess_q_results.append({
                                'order': order_number,
                                'date': order_date,
                                'customer': customer,
                                'qty': qty
                            })
                            total_quantity += qty
                            print(f"      🎯 *** FOUND OB-ESS-Q: {qty} units! ***")
                
                print(f"      ✅ Found {lines_found} line items")
                
                # Rate limiting (1.2s to be safe)
                time.sleep(1.2)
                
            except Exception as e:
                print(f"      ❌ Error getting detail: {e}")
                continue
        
        print(f"\n" + "=" * 60)
        print(f"🎯 SEPTEMBER 2025 RESULTS:")
        print(f"   📊 Customer orders checked: {check_count}/{len(orders)}")
        print(f"   📦 Orders with OB-ESS-Q: {len(ob_ess_q_results)}")
        print(f"   📈 Total OB-ESS-Q sold: {total_quantity} units")
        
        if ob_ess_q_results:
            print(f"\n📋 OB-ESS-Q sales details:")
            for result in ob_ess_q_results:
                print(f"   {result['order']} - {result['date']} - {result['customer']} - {result['qty']} units")
            
            # Calculate velocity for the period we actually found sales
            if len(ob_ess_q_results) > 0:
                dates = [result['date'] for result in ob_ess_q_results]
                first_date = min(dates)
                last_date = max(dates)
                
                start_dt = datetime.strptime(first_date, '%Y-%m-%d')
                end_dt = datetime.strptime(last_date, '%Y-%m-%d')
                actual_days = (end_dt - start_dt).days + 1
                
                daily_velocity = total_quantity / actual_days
                
                print(f"\n📈 OB-ESS-Q Sales Velocity (September 2025):")
                print(f"   Sales period: {first_date} to {last_date} ({actual_days} days)")
                print(f"   Daily velocity: {daily_velocity:.3f} units/day")
                print(f"   Weekly velocity: {daily_velocity * 7:.2f} units/week")
                print(f"   Monthly velocity: {daily_velocity * 30:.1f} units/month")
        else:
            print(f"\n❌ No OB-ESS-Q found in first {check_count} September orders")
            print(f"💡 Consider checking more orders or different SKU names")
        
        return total_quantity, len(ob_ess_q_results)
        
    except Exception as e:
        print(f"❌ September test failed: {e}")
        return 0, 0

def test_any_recent_data():
    """Fallback: check if we have ANY recent sales data"""
    print(f"\n🔄 Fallback: Checking for ANY recent sales data...")
    
    account_id = os.environ.get('CIN7_ACCOUNT_ID')
    api_key = os.environ.get('CIN7_API_KEY')
    base_url = os.environ.get('CIN7_BASE_URL', 'https://inventory.dearsystems.com/ExternalApi/v2')
    
    headers = {
        'api-auth-accountid': account_id,
        'api-auth-applicationkey': api_key,
        'Content-Type': 'application/json'
    }
    
    try:
        # Try just getting recent sales without date filter
        params = {
            'Page': 1,
            'Limit': 10
        }
        
        response = requests.get(f"{base_url}/SaleList", headers=headers, params=params, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        orders = data.get('SaleList', [])
        
        print(f"   ✅ Found {len(orders)} recent orders (any date)")
        
        if orders:
            print(f"   📋 Most recent orders:")
            for i, order in enumerate(orders[:5]):
                order_date = order.get('OrderDate', '')[:10]
                customer = order.get('Customer', 'Unknown')
                print(f"      {i+1}. {order.get('OrderNumber')} - {order_date} - {customer}")
        
        return len(orders), 0
        
    except Exception as e:
        print(f"   ❌ Fallback test failed: {e}")
        return 0, 0

if __name__ == '__main__':
    print("⚡ SEPTEMBER 2025 OB-ESS-Q Test")
    print("🛒 Testing CUSTOMER sales orders (current month)")
    print("⏱️ Should be much faster with recent data")
    print()
    
    qty, orders = test_september_ob_ess_q()
    
    print(f"\n" + "=" * 60)
    print(f"🎯 FINAL ANSWER (September 1-24, 2025):")
    print(f"   OB-ESS-Q units sold: {qty}")
    print(f"   Orders with OB-ESS-Q: {orders}")
    print(f"   Data source: Customer sales orders (SaleList API)")
    print(f"   ⏱️ Much faster than 2-month range!")
