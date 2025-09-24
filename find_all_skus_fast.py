"""
FAST approach: Get unique SKUs from a sample of orders
Instead of checking 10,000 orders, sample 50 and see what SKUs exist
"""
import requests
import os
import time
from dotenv import load_dotenv
from collections import defaultdict

load_dotenv()

def find_skus_fast():
    """Fast SKU discovery from sample orders"""
    account_id = os.environ.get('CIN7_ACCOUNT_ID')
    api_key = os.environ.get('CIN7_API_KEY')
    base_url = os.environ.get('CIN7_BASE_URL', 'https://inventory.dearsystems.com/ExternalApi/v2')
    
    headers = {
        'api-auth-accountid': account_id,
        'api-auth-applicationkey': api_key,
        'Content-Type': 'application/json'
    }
    
    print(f"⚡ FAST SKU Discovery")
    print(f"🎯 Goal: Find what SKUs exist (sample 50 orders)")
    print("=" * 50)
    
    try:
        # Get first page of orders
        params = {
            'Page': 1,
            'Limit': 50,  # Just 50 orders for speed
            'OrderDateFrom': '2025-09-01',
            'OrderDateTo': '2025-09-24'
        }
        
        response = requests.get(f"{base_url}/SaleList", headers=headers, params=params, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        orders = data.get('SaleList', [])
        
        print(f"📋 Found {len(orders)} orders to sample")
        
        if not orders:
            print("❌ No orders found")
            return
        
        # Sample dates
        print(f"📅 Date range in data:")
        dates = [order.get('OrderDate', '')[:10] for order in orders[:5]]
        print(f"   {min(dates)} to {max(dates)}")
        
        # Check sample orders for SKUs
        print(f"\n📦 Checking {len(orders)} orders for SKU patterns...")
        
        sku_counts = defaultdict(int)
        ob_related_skus = set()
        ob_ess_q_found = []
        
        for i, order in enumerate(orders):
            sale_id = order.get('SaleID')
            order_number = order.get('OrderNumber')
            order_date = order.get('OrderDate', '')[:10]
            
            if i % 10 == 0:
                print(f"   🔍 Checking order {i+1}/{len(orders)}...")
            
            # Skip voided
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
                
                # Check order lines
                order_data = detail.get('Order', {})
                
                if order_data.get('Lines'):
                    for line in order_data['Lines']:
                        sku = line.get('SKU', '').strip()
                        qty = line.get('Quantity', 0)
                        
                        if sku:
                            sku_counts[sku] += qty
                            
                            # Track OB-related SKUs
                            if 'OB' in sku.upper():
                                ob_related_skus.add(sku)
                            
                            # Check for exact match
                            if sku == 'OB-ESS-Q':
                                ob_ess_q_found.append({
                                    'order': order_number,
                                    'date': order_date,
                                    'qty': qty
                                })
                
                time.sleep(1.2)  # Rate limiting
                
            except Exception as e:
                print(f"\n   ❌ Error checking {order_number}: {e}")
                continue
        
        print(f"\n\n🎯 SKU ANALYSIS RESULTS:")
        print(f"   📊 Orders checked: {len(orders)}")
        print(f"   📦 Unique SKUs found: {len(sku_counts)}")
        print(f"   🔍 OB-related SKUs: {len(ob_related_skus)}")
        print(f"   🎯 OB-ESS-Q found: {len(ob_ess_q_found)} times")
        
        if ob_ess_q_found:
            total_qty = sum(item['qty'] for item in ob_ess_q_found)
            print(f"\n✅ OB-ESS-Q FOUND:")
            for item in ob_ess_q_found:
                print(f"   {item['order']} - {item['date']} - {item['qty']} units")
            print(f"   📈 Total: {total_qty} units")
        else:
            print(f"\n❌ OB-ESS-Q not found")
        
        # Show OB-related SKUs to help identify the right one
        if ob_related_skus:
            print(f"\n🔍 All OB-related SKUs found (might help identify correct SKU):")
            for sku in sorted(ob_related_skus):
                count = sku_counts[sku]
                print(f"   {sku} (sold {count} times)")
        
        # Show top 20 most common SKUs
        print(f"\n📊 Top 20 most sold SKUs (to understand the data):")
        top_skus = sorted(sku_counts.items(), key=lambda x: x[1], reverse=True)[:20]
        for sku, count in top_skus:
            print(f"   {sku}: {count} units")
        
        return len(ob_ess_q_found), sum(item['qty'] for item in ob_ess_q_found) if ob_ess_q_found else 0
        
    except Exception as e:
        print(f"❌ Fast SKU discovery failed: {e}")
        return 0, 0

if __name__ == '__main__':
    print("⚡ FAST SKU Discovery")
    print("🎯 Sample 50 orders to find SKU patterns")
    print("⏱️ Should take ~1 minute instead of 3+ hours")
    print()
    
    orders, qty = find_skus_fast()
    
    print(f"\n" + "=" * 50)
    print(f"⚡ SUMMARY:")
    print(f"   Orders with OB-ESS-Q: {orders}")
    print(f"   Total OB-ESS-Q units: {qty}")
    print(f"   ⏱️ Time saved: 99% (50 vs 10,000 orders)")
