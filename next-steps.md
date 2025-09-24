# Stock Forecasting App - Next Steps & Implementation Plan

## 🎯 Core Objective
Build a business-owner-friendly stock management system that ensures we never run out of stock while maintaining optimal inventory levels for all managed SKUs (OB-ESS-* and OB-ORG-* families).

---

## 📐 Mathematical Framework (Validated)

### Core Formulas

#### 1. **Sales Velocity Calculation**
```
Daily Velocity (V) = Total Units Sold ÷ Days in Period
Scaled Velocity (Vs) = V × Scale Factor
```

#### 2. **Lead Time Demand (LTD)**
```
LTD = Scaled Velocity × Lead Time Days
```
*Units we'll sell while waiting for new stock to arrive*

#### 3. **Safety Stock (SS)**
```
SS = Scaled Velocity × Buffer Stock Days
```
*Minimum stock level we must maintain*

#### 4. **Reorder Point (ROP)**
```
ROP = LTD + SS
```
*When stock hits this level, we MUST order*

#### 5. **Order Quantity Calculation**
```
If Current Stock ≤ ROP:
    Minimum Order = ROP - Current Stock + LTD
    
    This ensures:
    - We cover the deficit to reach ROP
    - Plus additional LTD to maintain stock during next lead time
```

### Example Validation
**Scenario**: SKU with 3 units/day velocity, 30-day lead time, 30-day buffer
- Scaled Velocity: 3 × 1.2 = 3.6 units/day
- LTD: 3.6 × 30 = 108 units
- SS: 3.6 × 30 = 108 units  
- ROP: 108 + 108 = 216 units

**If current stock = 50 units:**
- Days until stockout: 50 ÷ 3.6 = 13.9 days (CRITICAL!)
- Order needed: 216 - 50 + 108 = 274 units minimum

---

## 🏗️ UI/UX Architecture

### Navigation Structure
```
┌─────────────────────────────────────────┐
│  📊 Dashboard  │  📦 SKUs  │  ⚙️ Settings │
└─────────────────────────────────────────┘
```

### Page Layout Flow

#### **Dashboard Page** (Main)
```
Step 1: Business Parameters
├── Lead Time: [___] days
├── Buffer Stock: [___] months  
└── Scale Factor: [___] (growth multiplier)

Step 2: Analysis Period
├── From: [Date Picker]
├── To: [Date Picker]
└── [Analyze Period] button

Step 3: Sales Velocity Results
├── SKU Cards (filtered by OB-ESS-*, OB-ORG-*)
│   ├── Historical velocity
│   ├── Scaled velocity
│   └── Visual chart
└── Expandable details per SKU

Step 4: Reorder Points
├── Mathematical breakdown per SKU
├── LTD calculation shown
├── SS calculation shown
└── ROP = LTD + SS highlighted

Step 5: Current Stock Analysis
├── Current stock levels (from Cin7)
├── Status indicators (OK/Warning/Critical)
├── Days until stockout
└── Stock vs ROP comparison

Step 6: Order Recommendations
├── SKUs needing orders TODAY
├── Quantity calculations with math shown
├── Expected delivery dates
└── Post-delivery stock projections
```

#### **SKU Management Page** (New)
```
Active SKU Patterns:
├── OB-ESS-* [Active] [Remove]
├── OB-ORG-* [Active] [Remove]
└── [+ Add Pattern]

SKU List (matching patterns):
├── OB-ESS-Q (3 orders, 2.5/day)
├── OB-ESS-PGR-Q (5 orders, 1.2/day)
├── OB-ORG-500ML (8 orders, 0.8/day)
└── ... (paginated)
```

---

## 🔧 Technical Implementation Plan

### Phase 1: Backend Enhancements (Priority 1)
1. **Update `/api/analysis/period` endpoint**
   - Filter SKUs by pattern (OB-ESS-*, OB-ORG-*)
   - Add reorder point calculations
   - Include current stock levels (mock for now)

2. **Create `/api/stock/current` endpoint**
   - Mock current stock levels initially
   - Later integrate with Cin7 `/Product` endpoint

3. **Create `/api/recommendations` endpoint**
   - Calculate order requirements for all SKUs
   - Return prioritized list (critical first)

### Phase 2: Frontend Dashboard Rebuild (Priority 2)
1. **Update `templates/unified_dashboard.html`**
   - Implement 6-step flow
   - Add mathematical explanations
   - Show calculations transparently

2. **Add Visual Elements**
   - Progress bars for stock levels
   - Color coding (green/yellow/red)
   - Expandable math breakdowns

3. **Interactive Features**
   - Real-time recalculation on parameter changes
   - Export recommendations to CSV
   - Print-friendly order list

### Phase 3: SKU Management (Priority 3)
1. **Create SKU management page**
   - Pattern-based filtering
   - Add/remove patterns
   - View matching SKUs

2. **Persist SKU patterns**
   - Store in database
   - Apply to all calculations

### Phase 4: Real Stock Integration (Priority 4)
1. **Integrate Cin7 `/Product` endpoint**
   - Fetch real stock levels
   - Map to our SKU patterns
   - Cache for performance

2. **Add stock sync scheduling**
   - Periodic updates
   - Manual refresh option

---

## 📋 Database Schema Updates

### New Tables Needed

```sql
-- SKU patterns to monitor
CREATE TABLE sku_patterns (
    id INTEGER PRIMARY KEY,
    pattern TEXT NOT NULL UNIQUE,
    active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Current stock levels (cached)
CREATE TABLE stock_levels (
    id INTEGER PRIMARY KEY,
    sku TEXT NOT NULL UNIQUE,
    quantity INTEGER NOT NULL,
    warehouse TEXT,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Reorder history (for tracking)
CREATE TABLE reorder_history (
    id INTEGER PRIMARY KEY,
    sku TEXT NOT NULL,
    reorder_date DATE NOT NULL,
    quantity_ordered INTEGER NOT NULL,
    expected_delivery DATE,
    notes TEXT
);
```

---

## 🚀 Implementation Sequence

### Day 1: Backend Foundation
- [ ] Update `/api/analysis/period` with SKU filtering
- [ ] Add reorder point calculations to backend
- [ ] Create mock `/api/stock/current` endpoint
- [ ] Test mathematical accuracy with known examples

### Day 2: Frontend Core
- [ ] Rebuild dashboard with 6-step flow
- [ ] Add mathematical breakdowns
- [ ] Implement parameter inputs
- [ ] Connect to updated endpoints

### Day 3: Visual Polish
- [ ] Add status indicators
- [ ] Implement color coding
- [ ] Create expandable details
- [ ] Add loading states

### Day 4: SKU Management
- [ ] Create SKU patterns table
- [ ] Build SKU management page
- [ ] Implement pattern matching
- [ ] Test with OB-ESS-*, OB-ORG-*

### Day 5: Testing & Refinement
- [ ] End-to-end testing
- [ ] Mathematical validation
- [ ] UI/UX improvements
- [ ] Documentation

---

## ✅ Success Criteria

1. **Never Stockout**: System prevents stockouts with proper ROP calculations
2. **Clear Math**: Every calculation is transparent and verifiable
3. **Actionable**: Provides clear "order X units today" recommendations
4. **Scalable**: Handles multiple SKU patterns efficiently
5. **User-Friendly**: Business owners can understand and trust the system

---

## 🎨 UI Components Needed

### Status Indicators
```
✅ Healthy: Stock > ROP + 30 days
⚠️ Warning: Stock between ROP and ROP + 7 days  
🚨 Critical: Stock < ROP
💀 Stockout Risk: Will run out before delivery
```

### Calculation Cards
```
┌─────────────────────────────┐
│ OB-ESS-Q Reorder Calculation│
├─────────────────────────────┤
│ Daily Velocity: 3.0 units   │
│ × Scale Factor: 1.2         │
│ = Scaled: 3.6 units/day     │
├─────────────────────────────┤
│ Lead Time: 30 days          │
│ × 3.6 = 108 units (LTD)     │
├─────────────────────────────┤
│ Buffer: 30 days             │
│ × 3.6 = 108 units (SS)      │
├─────────────────────────────┤
│ ROP = 108 + 108 = 216 units │
└─────────────────────────────┘
```

---

## 🔍 Edge Cases to Handle

1. **New SKUs**: No sales history → Use category average or manual input
2. **Seasonal Items**: Allow manual velocity override
3. **Stockout Periods**: Exclude from velocity calculations
4. **Multiple Warehouses**: Calculate per warehouse
5. **Minimum Order Quantities**: Respect supplier MOQs

---

## 📊 Monitoring & Alerts

### Key Metrics to Track
- Stockout incidents (should be 0)
- Days of stock remaining per SKU
- Order recommendation accuracy
- Buffer stock utilization

### Alert Triggers
- Any SKU below ROP
- Predicted stockout within lead time
- Unusual velocity changes (>50% deviation)

---

## 🎯 Next Immediate Action

**Start with Phase 1, Step 1**: Update the `/api/analysis/period` endpoint to:
1. Filter for OB-ESS-* and OB-ORG-* SKUs
2. Add reorder point calculations
3. Return structured data for UI consumption

This will give us a solid foundation to build the UI on top of, with real calculations we can verify.
