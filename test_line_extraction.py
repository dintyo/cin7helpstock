"""
Test line extraction logic directly
"""
import requests
import os
import time
from dotenv import load_dotenv

load_dotenv()

def test_line_extraction():
    """Test extracting lines from a real order"""
    account_id = os.environ.get('CIN7_ACCOUNT_ID')
    api_key = os.environ.get('CIN7_API_KEY')
    base_url = os.environ.get('CIN7_BASE_URL', 'https://inventory.dearsystems.com/ExternalApi/v2')
    
    headers = {
        'api-auth-accountid': account_id,
        'api-auth-applicationkey': api_key,
        'Content-Type': 'application/json'
    }
    
    try:
        # Get a sample order
        print("🔍 Getting sample order...")
        list_params = {
            'Page': 1,
            'Limit': 1,
            'OrderDateFrom': '2025-08-01',
            'OrderDateTo': '2025-08-31'
        }
        
        response = requests.get(f"{base_url}/SaleList", headers=headers, params=list_params, timeout=30)
        response.raise_for_status()
        
        list_data = response.json()
        orders = list_data.get('SaleList', [])
        
        if not orders:
            print("❌ No orders found")
            return
        
        order = orders[0]
        sale_id = order.get('SaleID')
        order_number = order.get('OrderNumber')
        
        print(f"📋 Testing order: {order_number} (ID: {sale_id})")
        print(f"   Status: {order.get('Status')}")
        print(f"   Date: {order.get('OrderDate')}")
        
        # Get order detail
        time.sleep(2)  # Rate limiting
        
        detail_response = requests.get(f"{base_url}/Sale", headers=headers, params={'ID': sale_id}, timeout=30)
        detail_response.raise_for_status()
        
        detail = detail_response.json()
        
        # Test line extraction logic
        print(f"\n🔍 Line extraction test:")
        
        # Check pick lines
        pick_lines = []
        fulfilments = detail.get('Fulfilments', [])
        print(f"   Fulfilments found: {len(fulfilments)}")
        
        for i, fulfilment in enumerate(fulfilments):
            pick_data = fulfilment.get('Pick', {})
            print(f"   Fulfilment {i+1} Pick status: {pick_data.get('Status')}")
            
            if pick_data.get('Lines'):
                lines = pick_data['Lines']
                print(f"   Fulfilment {i+1} Pick lines: {len(lines)}")
                
                for line in lines:
                    pick_lines.append({
                        'sku': line.get('SKU', '').strip(),
                        'quantity': line.get('Quantity', 0),
                        'location': line.get('Location', ''),
                        'description': line.get('Name', '')
                    })
                    print(f"     - {line.get('SKU')}: {line.get('Quantity')} @ {line.get('Location')}")
        
        # Check order lines
        order_lines = []
        order_data = detail.get('Order', {})
        print(f"\n   Order section found: {bool(order_data)}")
        
        if order_data.get('Lines'):
            lines = order_data['Lines']
            print(f"   Order lines: {len(lines)}")
            
            for line in lines:
                order_lines.append({
                    'sku': line.get('SKU', '').strip(),
                    'quantity': line.get('Quantity', 0),
                    'location': None,
                    'description': line.get('Name', '')
                })
                print(f"     - {line.get('SKU')}: {line.get('Quantity')}")
        
        # Final decision
        lines_to_process = pick_lines if pick_lines else order_lines
        print(f"\n✅ FINAL: Using {len(lines_to_process)} lines from {'pick' if pick_lines else 'order'} source")
        
        for line in lines_to_process:
            print(f"   📦 {line['sku']}: {line['quantity']} units")
        
        return len(lines_to_process)
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return 0

if __name__ == '__main__':
    count = test_line_extraction()
    print(f"\n🎯 Result: {count} lines would be extracted")
