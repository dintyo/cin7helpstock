"""
Find OB-ESS-Q using CreatedSince (the working date filter)
Target: Last 30 days of REAL customer orders
"""
import requests
import os
import time
import sys
from dotenv import load_dotenv
from datetime import datetime, timedelta

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

def find_ob_ess_q_recent():
    """Find OB-ESS-Q in recent orders using CreatedSince"""
    account_id = os.environ.get('CIN7_ACCOUNT_ID')
    api_key = os.environ.get('CIN7_API_KEY')
    base_url = os.environ.get('CIN7_BASE_URL', 'https://inventory.dearsystems.com/ExternalApi/v2')
    
    headers = {
        'api-auth-accountid': account_id,
        'api-auth-applicationkey': api_key,
        'Content-Type': 'application/json'
    }
    
    # Use CreatedSince for last 30 days (the working approach)
    thirty_days_ago = datetime.now() - timedelta(days=30)
    created_since = thirty_days_ago.strftime('%Y-%m-%dT%H:%M:%SZ')
    
    print(f"🔍 Searching for OB-ESS-Q in RECENT customer orders")
    print(f"📅 Using CreatedSince: {created_since}")
    print(f"⏱️ Last 30 days of REAL data")
    print("=" * 60)
    
    try:
        # Step 1: Get ALL recent orders using CreatedSince
        print("📋 Step 1: Getting recent customer orders...")
        
        all_orders = []
        page = 1
        
        while page <= 10:  # Safety limit
            params = {
                'Page': page,
                'Limit': 1000,  # Max page size
                'CreatedSince': created_since
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
            time.sleep(1.2)  # Rate limiting
        
        print(f"   ✅ Total recent orders: {len(all_orders)}")
        
        if not all_orders:
            print("❌ No recent orders found")
            return 0, 0
        
        # Verify we have real recent dates
        print(f"\n📅 Verifying recent dates:")
        recent_dates = []
        for order in all_orders[:10]:
            order_date = order.get('OrderDate', '')[:10]
            recent_dates.append(order_date)
        
        unique_dates = sorted(set(recent_dates))
        print(f"   📅 Sample dates: {unique_dates[:5]}")
        
        # Check if we have real 2025 data
        has_2025_data = any('2025' in date for date in recent_dates)
        print(f"   ✅ Has 2025 data: {has_2025_data}")
        
        if not has_2025_data:
            print("   ⚠️ No 2025 data found - might be test account limitation")
        
        # Step 2: Search for OB-ESS-Q in ALL recent orders
        print(f"\n📦 Step 2: Searching {len(all_orders)} recent orders for OB-ESS-Q...")
        print(f"   ⏱️ Estimated time: {len(all_orders) * 1.2 / 60:.1f} minutes")
        
        ob_ess_q_results = []
        total_quantity = 0
        all_skus = set()
        ob_skus = set()
        
        for i, order in enumerate(all_orders):
            print_progress(i, len(all_orders), "Searching orders")
            
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
                        
                        if sku:
                            all_skus.add(sku)
                            
                            # Track OB-related SKUs
                            if 'OB' in sku.upper():
                                ob_skus.add(sku)
                            
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
        
        print_progress(len(all_orders), len(all_orders), "Searching orders")
        
        print(f"\n\n" + "=" * 60)
        print(f"🎯 RECENT ORDERS ANALYSIS:")
        print(f"   📊 Total orders checked: {len(all_orders)}")
        print(f"   📦 Orders with OB-ESS-Q: {len(ob_ess_q_results)}")
        print(f"   📈 Total OB-ESS-Q sold: {total_quantity} units")
        print(f"   🔍 Total unique SKUs: {len(all_skus)}")
        print(f"   🔍 OB-related SKUs: {len(ob_skus)}")
        
        if ob_ess_q_results:
            print(f"\n✅ OB-ESS-Q SALES FOUND:")
            for result in ob_ess_q_results:
                print(f"   {result['order']} - {result['date']} - {result['customer']} - {result['qty']} units")
            
            # Calculate velocity
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
            print(f"\n❌ No OB-ESS-Q found in recent orders")
            
            # Show OB-related SKUs for debugging
            if ob_skus:
                print(f"\n🔍 Found {len(ob_skus)} OB-related SKUs (might help identify correct SKU):")
                for sku in sorted(ob_skus)[:20]:  # Show first 20
                    print(f"   - {sku}")
                if len(ob_skus) > 20:
                    print(f"   ... and {len(ob_skus) - 20} more")
        
        return total_quantity, len(ob_ess_q_results)
        
    except Exception as e:
        print(f"❌ Recent search failed: {e}")
        return 0, 0

if __name__ == '__main__':
    print("⚡ OB-ESS-Q Search in Recent Orders")
    print("🔧 Using CreatedSince (the working date filter)")
    print("📊 Should find ~400 orders, not 10,000")
    print()
    
    qty, orders = find_ob_ess_q_recent()
    
    print(f"\n" + "=" * 60)
    print(f"🎯 FINAL ANSWER (Last 30 days):")
    print(f"   OB-ESS-Q units sold: {qty}")
    print(f"   Orders with OB-ESS-Q: {orders}")
    print(f"   Method: CreatedSince filter (working approach)")
