"""
Test script to verify warehouse-specific features
Tests all new endpoints without breaking existing functionality
"""
import os
from dotenv import load_dotenv
import requests
import json

load_dotenv()

BASE_URL = "http://localhost:5050"

def test_endpoint(name, endpoint, expected_keys=None):
    """Test a single endpoint"""
    try:
        print(f"\n{'='*80}")
        print(f"Testing: {name}")
        print(f"Endpoint: {endpoint}")
        print('-'*80)
        
        response = requests.get(f"{BASE_URL}{endpoint}", timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        print(f"✅ Status Code: {response.status_code}")
        print(f"✅ Response received successfully")
        
        if expected_keys:
            for key in expected_keys:
                if key in data:
                    print(f"✅ Contains '{key}' key")
                else:
                    print(f"❌ Missing '{key}' key")
                    return False
        
        # Show summary of data
        if 'success' in data:
            print(f"✅ Success: {data['success']}")
        
        if 'by_warehouse' in data:
            warehouses = list(data['by_warehouse'].keys())
            print(f"✅ Warehouses: {warehouses}")
            for wh in warehouses:
                items = data['by_warehouse'][wh]
                if isinstance(items, list):
                    print(f"   - {wh}: {len(items)} items")
        
        if 'stock_by_warehouse' in data:
            print(f"✅ Stock data contains {len(data['stock_by_warehouse'])} SKUs")
            # Show first SKU as example
            if data['stock_by_warehouse']:
                first_sku = list(data['stock_by_warehouse'].keys())[0]
                print(f"   Example: {first_sku} = {data['stock_by_warehouse'][first_sku]}")
        
        print(f"✅ {name} - PASSED")
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"❌ {name} - FAILED")
        print(f"   Error: {e}")
        return False
    except Exception as e:
        print(f"❌ {name} - FAILED")
        print(f"   Unexpected error: {e}")
        return False

def run_all_tests():
    """Run all tests"""
    print("="*80)
    print("WAREHOUSE FEATURES TEST SUITE")
    print("="*80)
    print("\nTesting both existing endpoints (backward compatibility)")
    print("and new warehouse-specific endpoints...")
    
    results = {}
    
    # Test parameters for analysis endpoints
    params = "?from=2025-08-01&to=2025-09-24&lead_time=30&buffer_months=1&scale_factor=1.0"
    
    # ========================================================================
    # Test EXISTING endpoints (should still work - backward compatibility)
    # ========================================================================
    print("\n" + "="*80)
    print("BACKWARD COMPATIBILITY TESTS")
    print("="*80)
    
    results['existing_period'] = test_endpoint(
        "Existing: Period Analysis (Aggregated)",
        f"/api/analysis/period{params}",
        ['success', 'skus', 'period']
    )
    
    results['existing_stock'] = test_endpoint(
        "Existing: Current Stock (Aggregated)",
        "/api/stock/current",
        ['success', 'stock_levels']
    )
    
    results['existing_recommendations'] = test_endpoint(
        "Existing: Recommendations (Aggregated)",
        f"/api/recommendations{params}",
        ['success', 'recommendations', 'summary']
    )
    
    # ========================================================================
    # Test NEW warehouse-specific endpoints
    # ========================================================================
    print("\n" + "="*80)
    print("NEW WAREHOUSE-SPECIFIC FEATURES")
    print("="*80)
    
    results['warehouse_period'] = test_endpoint(
        "NEW: Period Analysis by Warehouse",
        f"/api/analysis/period-by-warehouse{params}",
        ['success', 'by_warehouse', 'period']
    )
    
    results['warehouse_stock'] = test_endpoint(
        "NEW: Current Stock by Warehouse",
        "/api/stock/current-by-warehouse",
        ['success', 'stock_by_warehouse']
    )
    
    results['warehouse_recommendations'] = test_endpoint(
        "NEW: Recommendations by Warehouse",
        f"/api/recommendations-by-warehouse{params}",
        ['success', 'by_warehouse', 'summary_by_warehouse']
    )
    
    # ========================================================================
    # Test Summary
    # ========================================================================
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    failed = total - passed
    
    print(f"\nTotal Tests: {total}")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    
    print("\nDetailed Results:")
    for name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status} - {name}")
    
    if failed == 0:
        print("\n" + "="*80)
        print("🎉 ALL TESTS PASSED!")
        print("="*80)
        print("\n✅ Backward compatibility maintained")
        print("✅ New warehouse features working")
        print("\nYou can now access warehouse-specific views in the dashboard!")
    else:
        print("\n" + "="*80)
        print("⚠️  SOME TESTS FAILED")
        print("="*80)
        print("\nPlease check the errors above and ensure:")
        print("1. The Flask app is running (python unified_stock_app.py)")
        print("2. You have synced data using the dashboard")
        print("3. The database contains order data")
    
    return failed == 0

if __name__ == '__main__':
    print("\n⚠️  Make sure the Flask app is running before testing!")
    print("   Run: python unified_stock_app.py\n")
    
    input("Press Enter to start tests...")
    
    success = run_all_tests()
    
    if success:
        print("\n" + "="*80)
        print("WAREHOUSE MAPPING REFERENCE")
        print("="*80)
        print("\nDiscovered warehouse location codes:")
        print("  • CNTVIC  → VIC (Victoria)")
        print("  • WCLQLD  → QLD (Queensland)")
        print("  • WPKNSW  → NSW (Wetherill Park, New South Wales)")
        print("\nThese mappings are now implemented in unified_stock_app.py")
        print("="*80)

