"""
Test OB-ESS-Q sales with real-time progress indicators
"""
import requests
import os
import time
import sys
from dotenv import load_dotenv

load_dotenv()

def print_progress(current, total, prefix="Progress"):
    """Print progress bar"""
    percent = (current / total) * 100 if total > 0 else 0
    bar_length = 30
    filled_length = int(bar_length * current // total) if total > 0 else 0
    
    bar = '█' * filled_length + '-' * (bar_length - filled_length)
    sys.stdout.write(f'\r{prefix}: |{bar}| {current}/{total} ({percent:.1f}%)')
    sys.stdout.flush()

def test_ob_ess_q_with_progress():
    """Test OB-ESS-Q sales with progress indicators"""
    account_id = os.environ.get('CIN7_ACCOUNT_ID')
    api_key = os.environ.get('CIN7_API_KEY')
    base_url = os.environ.get('CIN7_BASE_URL', 'https://inventory.dearsystems.com/ExternalApi/v2')
    
    headers = {
        'api-auth-accountid': account_id,
        'api-auth-applicationkey': api_key,
        'Content-Type': 'application/json'
    }
    
    start_date = '2025-06-11'
    end_date = '2025-08-01'
    
    try:
        print(f"🔍 Searching for OB-ESS-Q sales from {start_date} to {end_date}")
        print("=" * 60)
        
        # Step 1: Get order list
        print("📋 Step 1: Getting order list...")
        
        params = {
            'Page': 1,
            'Limit': 100,
            'OrderDateFrom': start_date,
            'OrderDateTo': end_date
        }
        
        print("   🌐 Making API call to SaleList...")
        response = requests.get(f"{base_url}/SaleList", headers=headers, params=params, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        orders = data.get('SaleList', [])
        
        print(f"   ✅ Found {len(orders)} orders in period")
        
        if not orders:
            print("❌ No orders found - stopping")
            return 0, 0
        
        # Show sample dates to verify period
        print(f"   📅 Sample order dates:")
        for i, order in enumerate(orders[:3]):
            order_date = order.get('OrderDate', '')[:10]
            print(f"      {order.get('OrderNumber')} - {order_date}")
        
        # Step 2: Check each order for OB-ESS-Q
        print(f"\n📦 Step 2: Checking {len(orders)} orders for OB-ESS-Q...")
        print("   (This will take time due to rate limiting - 1.8s per order)")
        
        ob_ess_q_results = []
        total_quantity = 0
        
        for i, order in enumerate(orders):
            print_progress(i, len(orders), "Checking orders")
            
            sale_id = order.get('SaleID')
            order_number = order.get('OrderNumber')
            order_date = order.get('OrderDate', '')[:10]
            
            # Skip voided orders
            if order.get('Status', '').upper() == 'VOIDED':
                continue
            
            try:
                # Get order detail with progress
                detail_response = requests.get(f"{base_url}/Sale", 
                                             headers=headers, 
                                             params={'ID': sale_id}, 
                                             timeout=30)
                detail_response.raise_for_status()
                detail = detail_response.json()
                
                # Check pick lines first
                found_in_order = False
                
                # Check fulfilments/pick lines
                fulfilments = detail.get('Fulfilments', [])
                for fulfilment in fulfilments:
                    pick_data = fulfilment.get('Pick', {})
                    if pick_data.get('Lines'):
                        for line in pick_data['Lines']:
                            sku = line.get('SKU', '').strip()
                            if sku == 'OB-ESS-Q':
                                qty = line.get('Quantity', 0)
                                location = line.get('Location', '')
                                ob_ess_q_results.append({
                                    'order_number': order_number,
                                    'date': order_date,
                                    'quantity': qty,
                                    'location': location,
                                    'source': 'pick_line'
                                })
                                total_quantity += qty
                                found_in_order = True
                                print(f"\n   🎯 FOUND! {order_number} - {qty} OB-ESS-Q @ {location}")
                
                # Check order lines if not found in picks
                if not found_in_order:
                    order_data = detail.get('Order', {})
                    if order_data.get('Lines'):
                        for line in order_data['Lines']:
                            sku = line.get('SKU', '').strip()
                            if sku == 'OB-ESS-Q':
                                qty = line.get('Quantity', 0)
                                ob_ess_q_results.append({
                                    'order_number': order_number,
                                    'date': order_date,
                                    'quantity': qty,
                                    'location': 'order_line',
                                    'source': 'order_line'
                                })
                                total_quantity += qty
                                found_in_order = True
                                print(f"\n   🎯 FOUND! {order_number} - {qty} OB-ESS-Q (order line)")
                
                # Rate limiting
                time.sleep(1.8)
                
            except Exception as e:
                print(f"\n   ❌ Error checking {order_number}: {e}")
                continue
        
        print_progress(len(orders), len(orders), "Checking orders")
        print("\n" + "=" * 60)
        
        # Final results
        print(f"\n🎯 FINAL RESULTS for OB-ESS-Q ({start_date} to {end_date}):")
        print(f"   📊 Total orders with OB-ESS-Q: {len(ob_ess_q_results)}")
        print(f"   📦 Total OB-ESS-Q quantity sold: {total_quantity}")
        
        if ob_ess_q_results:
            print(f"\n📋 Detailed breakdown:")
            for result in ob_ess_q_results:
                print(f"   {result['order_number']} - {result['date']} - {result['quantity']} units - {result['location']}")
            
            # Calculate sales velocity
            if len(ob_ess_q_results) > 0:
                dates = [result['date'] for result in ob_ess_q_results]
                first_date = min(dates)
                last_date = max(dates)
                
                from datetime import datetime
                start_dt = datetime.strptime(first_date, '%Y-%m-%d')
                end_dt = datetime.strptime(last_date, '%Y-%m-%d')
                actual_days = (end_dt - start_dt).days + 1
                
                daily_velocity = total_quantity / actual_days
                
                print(f"\n📈 OB-ESS-Q Sales Velocity:")
                print(f"   Sales period: {first_date} to {last_date} ({actual_days} days)")
                print(f"   Daily velocity: {daily_velocity:.3f} units/day")
                print(f"   Weekly velocity: {daily_velocity * 7:.2f} units/week")
                print(f"   Monthly velocity: {daily_velocity * 30:.1f} units/month")
        else:
            print("❌ No OB-ESS-Q sales found in this period")
        
        return total_quantity, len(ob_ess_q_results)
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        return 0, 0

if __name__ == '__main__':
    print("🚀 Testing OB-ESS-Q Sales Analysis")
    print("⏱️  This will show progress bars and real-time updates")
    print()
    
    qty, orders = test_ob_ess_q_with_progress()
    
    print(f"\n" + "=" * 60)
    print(f"🎯 ANSWER:")
    print(f"   OB-ESS-Q units sold: {qty}")
    print(f"   Number of OB-ESS-Q orders: {orders}")
    print(f"   Period: 2025-06-11 to 2025-08-01 (inclusive)")
