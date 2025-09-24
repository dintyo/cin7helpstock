# Persistent Storage Setup for Render

## ✅ SQLite with Persistent Disk (Recommended)

Your app now supports persistent storage! Here's how to set it up:

### Step 1: Deploy Your App First
1. Follow the main deployment steps in `DEPLOYMENT.md`
2. Get your app running (data will be temporary at first)

### Step 2: Add Persistent Disk
1. In Render dashboard, go to your web service
2. Click **"Settings"** tab
3. Scroll down to **"Disks"** section
4. Click **"Add Disk"**
5. Configure:
   - **Name:** `app-data`
   - **Mount Path:** `/data/db`
   - **Size:** `5 GB` (as you've set up)
6. Click **"Save"**

### Step 3: Auto-Detection (No Setup Needed!)
**Good news:** With your `/data/db` mount path, the app will automatically:
- Detect the persistent disk
- Store database at `/data/db/stock_forecast.db`
- Store SKU selections at `/data/db/selected_skus.json`

**No environment variables needed!** ✅

### Step 4: Redeploy
1. Render will automatically redeploy with the new disk
2. Your database will now persist across restarts!

## 📊 What Gets Persisted

With persistent storage, you keep:
- ✅ **All synced order data** (sales history)
- ✅ **SKU selections** (your chosen products)
- ✅ **Product catalog** (SKU database)
- ✅ **Analysis history** (previous calculations)

## 💰 Cost

**Render Persistent Disk Pricing:**
- 5GB (your setup): ~$1.25/month
- 10GB: ~$2.50/month
- Excellent value for the storage!

Much cheaper than a full PostgreSQL instance for this use case!

## 🔧 Alternative: PostgreSQL

If you prefer PostgreSQL (better for high-traffic apps):

### Option A: Render PostgreSQL
1. Add **"PostgreSQL"** service in Render
2. Install `psycopg2` in requirements.txt
3. Update database connection code
4. Cost: ~$7/month minimum

### Option B: External PostgreSQL
1. Use services like:
   - **Supabase** (generous free tier)
   - **PlanetScale** (MySQL-compatible)
   - **Neon** (PostgreSQL, good free tier)
2. Update `DATABASE_URL` environment variable

## 🎯 Recommendation

**Start with persistent disk + SQLite** because:
- ✅ Cheapest option (~$0.25/month)
- ✅ No code changes needed
- ✅ Handles your current data volume easily
- ✅ Can migrate to PostgreSQL later if needed

## 🚨 Important Notes

1. **First Deploy:** Set up the disk BEFORE syncing lots of data
2. **Backup:** Render handles disk backups automatically
3. **Migration:** If you later want PostgreSQL, you can export SQLite data first
4. **Performance:** SQLite handles thousands of orders easily

## ✅ Verification

After setup, check persistence:
1. Sync some data
2. Restart your service (in Render dashboard)
3. Data should still be there!

Your stock forecasting app now has enterprise-grade persistence for under $1/month! 🎉
