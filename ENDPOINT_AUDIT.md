# CIN7 Data Sync Audit - All Endpoints

## ✅ ACTIVE ENDPOINTS USING REAL CIN7 DATA

### 1. `/api/analysis/period` ✅ SAFE
- **Purpose:** Calculate sales velocity for date range
- **Data Source:** Database (orders table from CIN7 sync)
- **Status:** ✅ Uses real order data
- **No hardcoded data**

### 2. `/api/recommendations` ✅ FIXED
- **Purpose:** Main reorder recommendations
- **Data Sources:**
  - Velocity: `get_period_analysis()` → database orders
  - Stock: `get_current_stock()` → **FIXED** to use live CIN7 sync
- **Status:** ✅ Now uses `sync_stock_from_cin7()` for real stock
- **Fixed:** Removed hardcoded stock dictionary

### 3. `/api/stock/current` ✅ FIXED  
- **Purpose:** Get current stock levels
- **Data Source:** **FIXED** to call `sync_stock_from_cin7()`
- **Status:** ✅ Fetches live from CIN7
- **Fixed:** Replaced hardcoded dictionary with live sync

### 4. `/api/analysis/period-by-warehouse` ✅ SAFE
- **Purpose:** Velocity by warehouse
- **Data Source:** Database (orders table with warehouse column)
- **Status:** ✅ Uses real order data grouped by warehouse
- **No hardcoded data**

### 5. `/api/stock/current-by-warehouse` ✅ SAFE
- **Purpose:** Stock levels split by warehouse  
- **Data Source:** Calls `sync_stock_from_cin7()` which returns `stock_by_warehouse`
- **Status:** ✅ Uses live CIN7 data with warehouse tracking
- **No hardcoded data**

### 6. `/api/recommendations-by-warehouse` ✅ SAFE
- **Purpose:** Reorder recommendations per warehouse
- **Data Sources:**
  - Velocity: `get_period_analysis_by_warehouse()` → database
  - Stock: `get_current_stock_by_warehouse()` → live CIN7
- **Status:** ✅ All data from CIN7
- **No hardcoded data**

### 7. `/api/sync/quick` ✅ SAFE
- **Purpose:** Quick sync button
- **Actions:** 
  - Syncs stock via `sync_stock_from_cin7()`
  - Syncs orders via `sync_recent_orders()`
- **Status:** ✅ Pure sync operation, no hardcoded data

---

## ⚠️ LEGACY/UNUSED ENDPOINTS

### `/api/analysis/reorder` ❌ NOT USED - HAS ISSUES
- **Purpose:** Business-focused reorder analysis (OLD)
- **Status:** ⚠️ NOT used by frontend
- **Problems:**
  1. Has mock stock: `current_stock = max(0, 100 - total_qty)` (line 1139)
  2. Has undefined variables: `from_date`, `to_date` (line 1120)
  3. Broken code - would error if called
- **Action:** Should be removed or fixed if needed

---

## 📊 DATA FLOW SUMMARY

### Stock Data Flow:
```
CIN7 API → sync_stock_from_cin7() → Returns {
  stock_levels: {sku: total},           // Aggregated
  stock_by_warehouse: {sku: {VIC: x, QLD: y, NSW: z}}  // Per warehouse
}
```

### Order Data Flow:
```
CIN7 API → sync_recent_orders() → Database orders table with warehouse column
```

### Recommendation Calculations:
```
1. Velocity: Database orders (real CIN7 synced data)
2. Stock: sync_stock_from_cin7() (live CIN7 API)
3. Calculate: Reorder point, order quantity
```

---

## ✅ VERIFICATION CHECKLIST

- [x] Main recommendations using live stock
- [x] Aggregated stock using live CIN7
- [x] Warehouse stock using live CIN7  
- [x] Warehouse recommendations using live CIN7
- [x] No hardcoded stock values in active code
- [x] All SKUs (including OBP, OBMT*, OB-MAX-*) fetch correctly
- [ ] Legacy `/api/analysis/reorder` removed or fixed

---

## 🔧 FIXES APPLIED

1. **`/api/stock/current`**
   - Before: Hardcoded dictionary with 12 SKUs
   - After: Calls `sync_stock_from_cin7()` for all SKUs

2. **`/api/recommendations`**  
   - Before: Used hardcoded stock via `get_current_stock()`
   - After: Uses live CIN7 stock via fixed `get_current_stock()`

---

## 🎯 RECOMMENDATION

**Delete `/api/analysis/reorder` endpoint** - It's:
- Not used by frontend
- Has mock data
- Has bugs (undefined variables)
- Superseded by `/api/recommendations`

All ACTIVE endpoints now use 100% real CIN7 data!

