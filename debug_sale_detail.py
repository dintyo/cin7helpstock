"""
Debug Sale detail API response to understand line extraction issue
"""
import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

def debug_sale_detail():
    """Debug what we get from Sale detail API"""
    account_id = os.environ.get('CIN7_ACCOUNT_ID')
    api_key = os.environ.get('CIN7_API_KEY')
    base_url = os.environ.get('CIN7_BASE_URL', 'https://inventory.dearsystems.com/ExternalApi/v2')
    
    headers = {
        'api-auth-accountid': account_id,
        'api-auth-applicationkey': api_key,
        'Content-Type': 'application/json'
    }
    
    try:
        # First get a sample order from SaleList
        print("🔍 Getting sample order from SaleList...")
        
        list_params = {
            'Page': 1,
            'Limit': 3,
            'OrderDateFrom': '2025-08-01',
            'OrderDateTo': '2025-08-31'
        }
        
        response = requests.get(f"{base_url}/SaleList", headers=headers, params=list_params, timeout=30)
        response.raise_for_status()
        
        list_data = response.json()
        orders = list_data.get('SaleList', [])
        
        if not orders:
            print("❌ No orders found in SaleList")
            return
        
        print(f"✅ Found {len(orders)} orders in list")
        
        # Test first order detail
        first_order = orders[0]
        sale_id = first_order.get('SaleID')
        order_number = first_order.get('OrderNumber')
        
        print(f"\n📋 Testing order detail for: {order_number} (ID: {sale_id})")
        
        # Get detailed order
        detail_params = {'ID': sale_id}
        detail_response = requests.get(f"{base_url}/Sale", headers=headers, params=detail_params, timeout=30)
        detail_response.raise_for_status()
        
        detail_data = detail_response.json()
        
        print(f"\n🔍 Sale detail structure:")
        print(f"   Top-level keys: {list(detail_data.keys())}")
        
        # Check for Order section
        if 'Order' in detail_data:
            order_section = detail_data['Order']
            print(f"\n📦 Order section keys: {list(order_section.keys())}")
            
            # Check for Lines
            if 'Lines' in order_section:
                lines = order_section['Lines']
                print(f"   ✅ Found {len(lines)} lines in Order.Lines")
                
                if lines:
                    sample_line = lines[0]
                    print(f"   📋 Sample line keys: {list(sample_line.keys())}")
                    print(f"   📋 Sample line: SKU={sample_line.get('SKU')}, Qty={sample_line.get('Quantity')}")
            else:
                print("   ❌ No 'Lines' in Order section")
        
        # Check for Fulfilments (pick lines)
        if 'Fulfilments' in detail_data:
            fulfilments = detail_data['Fulfilments']
            print(f"\n🚚 Found {len(fulfilments)} fulfilments")
            
            for i, fulfilment in enumerate(fulfilments):
                print(f"   Fulfilment {i+1} keys: {list(fulfilment.keys())}")
                
                if 'Pick' in fulfilment:
                    pick = fulfilment['Pick']
                    print(f"   Pick keys: {list(pick.keys())}")
                    
                    if 'Lines' in pick:
                        pick_lines = pick['Lines']
                        print(f"   ✅ Found {len(pick_lines)} pick lines")
                        
                        if pick_lines:
                            sample_pick = pick_lines[0]
                            print(f"   📋 Sample pick line: SKU={sample_pick.get('SKU')}, Qty={sample_pick.get('Quantity')}, Location={sample_pick.get('Location')}")
        
        # Show raw structure for debugging
        print(f"\n📄 Raw detail structure (first 1000 chars):")
        print(json.dumps(detail_data, indent=2)[:1000] + "...")
        
    except Exception as e:
        print(f"❌ Debug failed: {e}")

if __name__ == '__main__':
    debug_sale_detail()
