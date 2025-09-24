"""
Check ALL September 2025 orders for OB-ESS-Q
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

def check_all_september_orders():
    """Check ALL September orders for OB-ESS-Q"""
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
    
    print(f"🔍 Checking ALL September 2025 customer orders for OB-ESS-Q")
    print(f"📅 Period: {start_date} to {end_date}")
    print("=" * 60)
    
    try:
        # Step 1: Get ALL customer sales orders for September
        print("📋 Step 1: Getting ALL customer sales orders...")
        
        all_orders = []
        page = 1
        
        while page <= 10:  # Safety limit
            params = {
                'Page': page,
                'Limit': 1000,  # Max page size
                'OrderDateFrom': start_date,
                'OrderDateTo': end_date
            }
            
            response = requests.get(f"{base_url}/SaleList", headers=headers, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            orders = data.get('SaleList', [])
            
            print(f"   📄 Page {page}: {len(orders)} orders")
            
            if not orders:
                break
            
            all_orders.extend(orders)
            
            if len(orders) < 1000:
                break
            
            page += 1
            time.sleep(1.2)  # Rate limiting between pages
        
        print(f"   ✅ Total orders found: {len(all_orders)}")
        
        if not all_orders:
            print("❌ No orders found")
            return 0, 0
        
        # Show sample dates to verify what we actually got
        print(f"\n📅 Sample order dates (checking for date range issues):")
        for i, order in enumerate(all_orders[:5]):
            order_date = order.get('OrderDate', '')[:10]
            print(f"   {i+1}. {order.get('OrderNumber')} - {order_date}")
        
        # Step 2: Check ALL orders for OB-ESS-Q
        print(f"\n📦 Step 2: Checking ALL {len(all_orders)} orders for OB-ESS-Q...")
        print(f"   ⏱️ Estimated time: {len(all_orders) * 1.2 / 60:.1f} minutes")
        print(f"   🔍 Looking for exact SKU: 'OB-ESS-Q'")
        
        ob_ess_q_results = []
        total_quantity = 0
        all_skus_found = set()
        
        for i, order in enumerate(all_orders):
            print_progress(i, len(all_orders), "Checking orders")
            
            sale_id = order.get('SaleID')
            order_number = order.get('OrderNumber')
            order_date = order.get('OrderDate', '')[:10]
            customer = order.get('Customer', 'Unknown')
            
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
                
                # Check customer order lines
                order_data = detail.get('Order', {})
                
                if order_data.get('Lines'):
                    for line in order_data['Lines']:
                        sku = line.get('SKU', '').strip()
                        qty = line.get('Quantity', 0)
                        
                        # Track all SKUs for analysis
                        all_skus_found.add(sku)
                        
                        # Check for exact match
                        if sku == 'OB-ESS-Q':
                            ob_ess_q_results.append({
                                'order': order_number,
                                'date': order_date,
                                'customer': customer,
                                'qty': qty
                            })
                            total_quantity += qty
                            print(f"\n   🎯 FOUND OB-ESS-Q: {order_number} - {customer} - {qty} units")
                
                time.sleep(1.2)  # Rate limiting
                
            except Exception as e:
                print(f"\n   ❌ Error checking {order_number}: {e}")
                continue
        
        print_progress(len(all_orders), len(all_orders), "Checking orders")
        
        print(f"\n\n" + "=" * 60)
        print(f"🎯 COMPLETE SEPTEMBER 2025 RESULTS:")
        print(f"   📊 Total orders checked: {len(all_orders)}")
        print(f"   📦 Orders with OB-ESS-Q: {len(ob_ess_q_results)}")
        print(f"   📈 Total OB-ESS-Q sold: {total_quantity} units")
        
        if ob_ess_q_results:
            print(f"\n📋 All OB-ESS-Q sales:")
            for result in ob_ess_q_results:
                print(f"   {result['order']} - {result['date']} - {result['customer']} - {result['qty']} units")
            
            # Calculate velocity
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
            print(f"\n❌ No OB-ESS-Q found in ANY September orders")
            
            # Show similar SKUs for debugging
            ob_skus = [sku for sku in all_skus_found if 'OB' in sku.upper()]
            if ob_skus:
                print(f"\n🔍 Found {len(ob_skus)} similar 'OB' SKUs:")
                for sku in sorted(ob_skus)[:20]:  # Show first 20
                    print(f"   - {sku}")
                if len(ob_skus) > 20:
                    print(f"   ... and {len(ob_skus) - 20} more")
            
            print(f"\n📊 Total unique SKUs found: {len(all_skus_found)}")
        
        return total_quantity, len(ob_ess_q_results)
        
    except Exception as e:
        print(f"❌ September check failed: {e}")
        return 0, 0

if __name__ == '__main__':
    print("🔍 COMPLETE September 2025 OB-ESS-Q Analysis")
    print("🛒 Checking ALL customer sales orders")
    print("⏱️ Will take a few minutes due to rate limiting...")
    print()
    
    qty, orders = check_all_september_orders()
    
    print(f"\n" + "=" * 60)
    print(f"🎯 FINAL ANSWER (September 1-24, 2025):")
    print(f"   OB-ESS-Q units sold: {qty}")
    print(f"   Orders containing OB-ESS-Q: {orders}")
    print(f"   Data source: ALL customer sales orders via SaleList API")
