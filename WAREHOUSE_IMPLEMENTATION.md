# Warehouse-Specific Analysis Implementation

## Overview
This document describes the warehouse-specific stock analysis and reorder recommendations feature that was added to the OBStock application.

## Warehouse Codes Discovered
Through querying the CIN7 API `/ref/location` endpoint, the following warehouse location codes were identified:

- **CNTVIC** → VIC (Victoria)
- **WCLQLD** → QLD (Queensland)  
- **WPKNSW** → NSW (Wetherill Park, New South Wales)

## Changes Made

### 1. Backend Changes (`unified_stock_app.py`)

#### Updated Warehouse Mappings
- Added WPKNSW mapping for NSW warehouse in all sync methods
- Updated `sync_date_window()` (lines ~206-214)
- Updated `sync_recent_orders()` (lines ~453-461)

#### Enhanced Stock Sync
- Modified `sync_stock_from_cin7()` method to track stock by warehouse
- Now returns both aggregated stock (backward compatible) and warehouse-specific stock
- New response format includes `stock_by_warehouse` field: `{sku: {VIC: amount, QLD: amount, NSW: amount}}`

#### New API Endpoints (Non-Breaking)

All new endpoints have `-by-warehouse` suffix to avoid conflicts:

**`/api/analysis/period-by-warehouse`**
- Calculates sales velocity per warehouse per SKU
- Same parameters as existing `/api/analysis/period`
- Returns: `{by_warehouse: {VIC: [...], QLD: [...], NSW: [...]}}`

**`/api/stock/current-by-warehouse`**
- Fetches live stock levels split by warehouse from CIN7
- Returns: `{stock_by_warehouse: {sku: {VIC: amount, QLD: amount, NSW: amount}}}`

**`/api/recommendations-by-warehouse`**
- Core feature: Per-warehouse reorder recommendations
- Calculates warehouse-specific:
  - Velocity
  - Current stock levels
  - Reorder points
  - Order quantities needed
- Returns recommendations grouped by warehouse with summaries

### 2. Frontend Changes (`templates/enhanced_reorder_dashboard.html`)

#### New UI Components

**Warehouse View Toggle**
- Button appears after running analysis: "🏭 View by Warehouse →"
- Toggles between aggregated and warehouse-specific views
- Non-destructive - can switch back and forth

**Warehouse Tabs**
- Three tabs: VIC (Victoria), QLD (Queensland), NSW (Wetherill Park)
- Shows warehouse-specific data when clicked

**Warehouse Summary Cards**
- Critical/Urgent/Orders Needed/Total Units per warehouse
- Color-coded same as main dashboard

**Warehouse Recommendations Table**
- Same columns as main table but filtered by warehouse
- Shows SKU, Urgency, Stock, Velocity, Reorder Point, Order Quantity
- Empty state when warehouse has no issues

#### JavaScript Functions Added
- `loadWarehouseData()` - Fetches warehouse-specific recommendations
- `toggleWarehouseView()` - Switches between views
- `showWarehouse(warehouse)` - Displays specific warehouse data
- `displayWarehouseRecommendations(warehouse)` - Populates table

## Backward Compatibility

✅ **All existing functionality preserved:**
- Existing endpoints unchanged
- Aggregated view still the default
- Warehouse view is opt-in via toggle button
- No database schema changes required

## Usage

### For Users

1. **Run Analysis** (same as before)
   - Set business parameters
   - Choose analysis period
   - Click "Calculate Analysis"

2. **View Aggregated Results** (default)
   - See total stock and recommendations across all warehouses

3. **Switch to Warehouse View** (NEW)
   - Click "🏭 View by Warehouse" button
   - Select warehouse tab (VIC/QLD/NSW)
   - View warehouse-specific recommendations
   - Switch back anytime with "← Back to Aggregated View"

### For Developers

**Testing the new endpoints:**
```bash
# Run the test suite
python test_warehouse_features.py

# Manual API testing
curl "http://localhost:5050/api/analysis/period-by-warehouse?from=2025-08-01&to=2025-09-24&lead_time=30&buffer_months=1&scale_factor=1.0"
curl "http://localhost:5050/api/stock/current-by-warehouse"
curl "http://localhost:5050/api/recommendations-by-warehouse?from=2025-08-01&to=2025-09-24"
```

## Benefits

1. **Warehouse-Specific Insights**
   - See which warehouse needs restocking
   - Identify location-specific stock issues
   - Plan orders per warehouse location

2. **Better Inventory Planning**
   - Avoid over-ordering at one location while another is low
   - Balance stock across warehouses
   - Location-specific velocity tracking

3. **No Disruption**
   - Existing workflows unchanged
   - Opt-in feature
   - Easy to toggle between views

## Files Modified

- `unified_stock_app.py` - Backend API endpoints and warehouse mappings
- `templates/enhanced_reorder_dashboard.html` - Frontend UI and JavaScript
- `test_warehouse_features.py` - Test suite for new features

## Files Created (Temporary)

- `warehouse_locations.json` - CIN7 location data (for reference)

## Next Steps

Consider these enhancements:
- Add warehouse filter to existing aggregated view
- Export warehouse-specific recommendations to separate CSV files
- Add warehouse comparison charts
- Track inter-warehouse transfers
- Historical warehouse performance metrics

