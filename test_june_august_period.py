"""
Test the specific period: June 11, 2025 to August 1, 2025
Look for OB-ESS-Q sales specifically
"""
import requests
import os
import time
from dotenv import load_dotenv

load_dotenv()

def test_june_august_period():
    """Test the specific period for OB-ESS-Q sales"""
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
        print(f"🔍 Testing period: {start_date} to {end_date}")
        print("Looking specifically for OB-ESS-Q sales...")
        
        # Get orders for this period
        params = {
            'Page': 1,
            'Limit': 100,  # Get more orders to find OB-ESS-Q
            'OrderDateFrom': start_date,
            'OrderDateTo': end_date
        }
        
        response = requests.get(f"{base_url}/SaleList", headers=headers, params=params, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        orders = data.get('SaleList', [])
        
        print(f"📊 Found {len(orders)} orders in period")
        
        if not orders:
            print("❌ No orders found in this period")
            return
        
        # Show sample of order dates to verify period
        print(f"\n📅 Sample order dates:")
        for i, order in enumerate(orders[:5]):
            order_date = order.get('OrderDate', '')[:10]
            print(f"   {i+1}. {order.get('OrderNumber')} - {order_date} - {order.get('Status')}")
        
        # Check each order for OB-ESS-Q
        ob_ess_q_orders = []
        ob_ess_q_total_qty = 0
        
        print(f"\n🔍 Checking {len(orders)} orders for OB-ESS-Q...")
        
        for i, order in enumerate(orders):
            if i % 10 == 0:
                print(f"   Checked {i}/{len(orders)} orders...")
            
            sale_id = order.get('SaleID')
            order_number = order.get('OrderNumber')
            
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
                
                # Check pick lines first (more accurate)
                found_in_picks = False
                fulfilments = detail.get('Fulfilments', [])
                
                for fulfilment in fulfilments:
                    pick_data = fulfilment.get('Pick', {})
                    if pick_data.get('Lines'):
                        for line in pick_data['Lines']:
                            sku = line.get('SKU', '').strip()
                            if sku == 'OB-ESS-Q':
                                qty = line.get('Quantity', 0)
                                location = line.get('Location', '')
                                ob_ess_q_orders.append({
                                    'order_number': order_number,
                                    'date': order.get('OrderDate', '')[:10],
                                    'quantity': qty,
                                    'location': location,
                                    'source': 'pick'
                                })
                                ob_ess_q_total_qty += qty
                                found_in_picks = True
                                print(f"   ✅ Found OB-ESS-Q in {order_number}: {qty} units @ {location}")
                
                # Check order lines if not found in picks
                if not found_in_picks:
                    order_data = detail.get('Order', {})
                    if order_data.get('Lines'):
                        for line in order_data['Lines']:
                            sku = line.get('SKU', '').strip()
                            if sku == 'OB-ESS-Q':
                                qty = line.get('Quantity', 0)
                                ob_ess_q_orders.append({
                                    'order_number': order_number,
                                    'date': order.get('OrderDate', '')[:10],
                                    'quantity': qty,
                                    'location': 'order_line',
                                    'source': 'order'
                                })
                                ob_ess_q_total_qty += qty
                                print(f"   ✅ Found OB-ESS-Q in {order_number}: {qty} units (order line)")
                
                time.sleep(1.8)  # Rate limiting for detail calls
                
            except Exception as e:
                print(f"   ❌ Error processing {order_number}: {e}")
                continue
        
        print(f"\n🎯 RESULTS for {start_date} to {end_date}:")
        print(f"   📊 Total OB-ESS-Q orders: {len(ob_ess_q_orders)}")
        print(f"   📦 Total OB-ESS-Q quantity: {ob_ess_q_total_qty}")
        
        if ob_ess_q_orders:
            print(f"\n📋 OB-ESS-Q order details:")
            for order in ob_ess_q_orders:
                print(f"   {order['order_number']} - {order['date']} - {order['quantity']} units @ {order['location']}")
            
            # Calculate velocity
            if len(ob_ess_q_orders) > 0:
                # Calculate actual sales period
                dates = [order['date'] for order in ob_ess_q_orders]
                first_date = min(dates)
                last_date = max(dates)
                
                from datetime import datetime
                start_dt = datetime.strptime(first_date, '%Y-%m-%d')
                end_dt = datetime.strptime(last_date, '%Y-%m-%d')
                actual_days = (end_dt - start_dt).days + 1
                
                daily_velocity = ob_ess_q_total_qty / actual_days
                
                print(f"\n📈 OB-ESS-Q Sales Velocity:")
                print(f"   Sales period: {first_date} to {last_date} ({actual_days} days)")
                print(f"   Daily velocity: {daily_velocity:.2f} units/day")
                print(f"   Weekly velocity: {daily_velocity * 7:.2f} units/week")
                print(f"   Monthly velocity: {daily_velocity * 30:.2f} units/month")
        
        return ob_ess_q_total_qty, len(ob_ess_q_orders)
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return 0, 0

if __name__ == '__main__':
    qty, orders = test_june_august_period()
    print(f"\n🎯 FINAL ANSWER:")
    print(f"   OB-ESS-Q quantity sold: {qty}")
    print(f"   Number of orders: {orders}")
