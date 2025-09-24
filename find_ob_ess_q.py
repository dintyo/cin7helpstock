"""
Find OB-ESS-Q sales from June 11, 2025 to August 1, 2025
Using correct SaleList API (customer orders, not purchase orders)
"""
import requests
import os
import time
import sys
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

def print_progress(current, total, prefix="Progress"):
    """Print progress bar"""
    if total == 0:
        return
    percent = (current / total) * 100
    bar_length = 30
    filled_length = int(bar_length * current // total)
    
    bar = '█' * filled_length + '-' * (bar_length - filled_length)
    sys.stdout.write(f'\r{prefix}: |{bar}| {current}/{total} ({percent:.1f}%)')
    sys.stdout.flush()

def find_ob_ess_q_sales():
    """Find OB-ESS-Q sales in the specified period"""
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
    
    print(f"🔍 Searching for OB-ESS-Q in CUSTOMER SALES ORDERS")
    print(f"📅 Period: {start_date} to {end_date} (inclusive)")
    print(f"🌐 Using SaleList API (customer orders)")
    print("=" * 60)
    
    try:
        # Step 1: Get all sales orders for the period
        print("📋 Step 1: Getting customer sales orders...")
        
        all_orders = []
        page = 1
        
        while page <= 10:  # Safety limit
            print(f"   🌐 Fetching page {page}...")
            
            params = {
                'Page': page,
                'Limit': 1000,  # Use max page size
                'OrderDateFrom': start_date,
                'OrderDateTo': end_date
            }
            
            response = requests.get(f"{base_url}/SaleList", headers=headers, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            orders = data.get('SaleList', [])
            
            print(f"   ✅ Found {len(orders)} orders on page {page}")
            
            if not orders:
                break
            
            # Show sample order info
            if page == 1 and orders:
                sample = orders[0]
                print(f"   📋 Sample order: {sample.get('OrderNumber')} - {sample.get('OrderDate')[:10]} - {sample.get('Status')}")
            
            all_orders.extend(orders)
            
            if len(orders) < 1000:
                break
            
            page += 1
            time.sleep(1.5)  # Rate limiting
        
        print(f"\n📊 Total orders found: {len(all_orders)}")
        
        if not all_orders:
            print("❌ No orders found in period")
            return 0, 0
        
        # Step 2: Check each order for OB-ESS-Q
        print(f"\n📦 Step 2: Checking {len(all_orders)} orders for OB-ESS-Q...")
        print("   ⏱️ This will take time due to rate limiting...")
        
        ob_ess_q_results = []
        total_quantity = 0
        checked_count = 0
        
        for order in all_orders:
            checked_count += 1
            print_progress(checked_count, len(all_orders), "Checking orders")
            
            sale_id = order.get('SaleID')
            order_number = order.get('OrderNumber')
            order_date = order.get('OrderDate', '')[:10]
            
            # Skip voided orders
            if order.get('Status', '').upper() == 'VOIDED':
                continue
            
            try:
                # Get order detail
                detail_response = requests.get(f"{base_url}/Sale", 
                                             headers=headers, 
                                             params={'ID': sale_id}, 
                                             timeout=30)
                detail_response.raise_for_status()
                detail = detail_response.json()
                
                # Check order lines (customer order lines)
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
                                'source': 'customer_order'
                            })
                            total_quantity += qty
                            print(f"\n   🎯 FOUND OB-ESS-Q! {order_number} - {order_date} - {qty} units")
                
                # Rate limiting (critical!)
                time.sleep(1.8)
                
            except Exception as e:
                print(f"\n   ❌ Error checking {order_number}: {e}")
                continue
        
        print_progress(len(all_orders), len(all_orders), "Checking orders")
        print("\n" + "=" * 60)
        
        # Results
        print(f"\n🎯 FINAL RESULTS for OB-ESS-Q ({start_date} to {end_date}):")
        print(f"   📊 Total orders checked: {len(all_orders)}")
        print(f"   📦 Orders with OB-ESS-Q: {len(ob_ess_q_results)}")
        print(f"   📈 Total OB-ESS-Q quantity: {total_quantity}")
        
        if ob_ess_q_results:
            print(f"\n📋 OB-ESS-Q order details:")
            for result in ob_ess_q_results:
                print(f"   {result['order_number']} - {result['date']} - {result['quantity']} units")
            
            # Calculate sales velocity
            if len(ob_ess_q_results) > 0:
                dates = [result['date'] for result in ob_ess_q_results]
                first_date = min(dates)
                last_date = max(dates)
                
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
            print("\n❌ No OB-ESS-Q found in customer sales orders")
        
        return total_quantity, len(ob_ess_q_results)
        
    except Exception as e:
        print(f"\n❌ Search failed: {e}")
        return 0, 0

if __name__ == '__main__':
    print("🚀 OB-ESS-Q Sales Analysis")
    print("🛒 Searching CUSTOMER SALES ORDERS (not purchase orders)")
    print()
    
    qty, orders = find_ob_ess_q_sales()
    
    print(f"\n" + "=" * 60)
    print(f"🎯 FINAL ANSWER:")
    print(f"   OB-ESS-Q units sold: {qty}")
    print(f"   Number of orders with OB-ESS-Q: {orders}")
    print(f"   Period: June 11, 2025 to August 1, 2025 (inclusive)")
    print(f"   Source: Customer sales orders via Cin7 SaleList API")
