# Automated Daily Sync Setup

Your app already has everything needed for automated daily syncing! Here's how to set it up:

## 🎯 What Gets Synced Daily

1. **Stock Levels** - Current inventory from Cin7 (all SKUs)
2. **Recent Orders** - Last 7 days of orders (catches any new sales)

## 🔧 Setup Instructions

### Step 1: Add Security Token to Render

1. Go to your Render dashboard
2. Open your `obstock` web service
3. Go to **"Environment"** tab
4. Add a new environment variable:
   - **Key:** `CRON_TOKEN`
   - **Value:** (generate a random secure token)
   
   **Generate a token:**
   ```bash
   # Run this locally to generate a secure random token:
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```
   
   Example: `xK3mP9nQ2wR5tY8uI1oP4aS7dF6gH0jK1lZ3xC5vB2nM`

4. Click **"Save Changes"** (Render will redeploy)

### Step 2: Test the Endpoint

Once deployed, test it manually:

```bash
# Replace with your actual Render URL and token
curl -X POST "https://your-app.onrender.com/api/cron/daily-sync?cron_token=YOUR_TOKEN_HERE"
```

You should see a JSON response with sync results.

### Step 3: Set Up Automated Scheduling

Choose **ONE** of these free options:

---

## Option A: cron-job.org (Recommended - 100% Free)

**Best for: Simple, reliable, free forever**

1. Go to https://cron-job.org/en/
2. Sign up for free account (no credit card needed)
3. Click **"Create cronjob"**
4. Configure:
   - **Title:** "Obstock Daily Sync"
   - **URL:** `https://your-app.onrender.com/api/cron/daily-sync?cron_token=YOUR_TOKEN`
   - **Schedule:** 
     - Pattern: `0 2 * * *` (runs at 2 AM daily)
     - Or use their visual scheduler
   - **Request method:** POST
   - **Notifications:** Enable email on failure
5. Save!

**Pros:**
- ✅ 100% free forever
- ✅ Reliable
- ✅ Email notifications
- ✅ Simple interface

---

## Option B: EasyCron (Free Tier)

**Best for: More advanced features**

1. Go to https://www.easycron.com/
2. Sign up (free tier: 20 jobs)
3. Add new cron job:
   - **URL:** `https://your-app.onrender.com/api/cron/daily-sync?cron_token=YOUR_TOKEN`
   - **Cron expression:** `0 2 * * *` (2 AM daily)
   - **Time zone:** Your timezone
   - **HTTP Method:** POST
4. Save

---

## Option C: Render Cron Jobs (Paid)

**Best for: Integrated solution (costs ~$7/month)**

If you prefer everything in Render:

1. In Render dashboard, click **"New +"**
2. Select **"Cron Job"**
3. Connect your GitHub repo
4. Configure:
   - **Command:** `python daily_sync.py`
   - **Schedule:** `0 2 * * *`
5. Set same environment variables as web service
6. Deploy

**Pros:**
- ✅ Fully integrated with Render
- ✅ Runs on same infrastructure
- ✅ Direct database access

**Cons:**
- ❌ Costs money ($7/month for smallest plan)

---

## Option D: GitHub Actions (Free)

**Best for: Developers who use GitHub**

Create `.github/workflows/daily-sync.yml`:

```yaml
name: Daily Sync
on:
  schedule:
    - cron: '0 2 * * *'  # 2 AM UTC daily
  workflow_dispatch:  # Allow manual trigger

jobs:
  sync:
    runs-on: ubuntu-latest
    steps:
      - name: Trigger Daily Sync
        run: |
          curl -X POST "${{ secrets.RENDER_SYNC_URL }}?cron_token=${{ secrets.CRON_TOKEN }}"
```

Add secrets to your GitHub repo:
- `RENDER_SYNC_URL`: `https://your-app.onrender.com/api/cron/daily-sync`
- `CRON_TOKEN`: Your generated token

---

## 🎯 Recommended Setup

**For most users, I recommend Option A (cron-job.org):**
- ✅ Free forever
- ✅ Dead simple to set up
- ✅ Reliable
- ✅ Email alerts if sync fails
- ✅ Takes 5 minutes to configure

---

## 🔍 Monitoring Your Syncs

### Check Sync Logs

1. Visit your Render dashboard
2. Go to your web service
3. Click **"Logs"** tab
4. Look for daily sync entries:
   ```
   🔄 Starting automated daily sync via cron endpoint
   ✅ Automated daily sync completed successfully
   ```

### Check Sync Status via API

```bash
curl https://your-app.onrender.com/api/sync/status
```

### Review Daily Sync Log File

On Render, your sync creates a log file:
```bash
# In Render Shell:
tail -50 daily_sync.log
```

---

## ⏰ Best Time to Run

**Recommended: 2 AM in your timezone**

Why?
- ✅ Low traffic time
- ✅ Won't interfere with daytime usage
- ✅ Data is fresh by morning

Adjust the cron schedule if needed:
- `0 2 * * *` - 2 AM daily
- `0 1 * * *` - 1 AM daily
- `0 6 * * *` - 6 AM daily
- `0 */6 * * *` - Every 6 hours

---

## 🧪 Testing

### Manual Test (Render Shell)
```bash
python daily_sync.py
```

### API Test
```bash
curl -X POST "https://your-app.onrender.com/api/cron/daily-sync?cron_token=YOUR_TOKEN"
```

### Expected Response
```json
{
  "success": true,
  "orders": {
    "success": true,
    "orders": 15,
    "lines": 23
  },
  "stock": {
    "success": true,
    "skus": 10,
    "total_units": 1292
  },
  "timestamp": "2025-11-25T10:30:45.123456"
}
```

---

## 🛡️ Security

Your sync endpoint is protected by:
1. **Token authentication** - Only requests with correct token work
2. **Environment variable** - Token never in code
3. **Logs sanitized** - Token not logged

**Keep your CRON_TOKEN secret!** Don't share it or commit it to git.

---

## 📊 What Happens Each Day

```
2:00 AM → Cron service triggers sync
          ↓
2:00 AM → Your app receives request
          ↓
2:00 AM → Sync stock levels (2-3 min)
          ↓
2:03 AM → Sync recent orders (5-10 min)
          ↓
2:13 AM → Database updated
          ↓
Morning → Fresh data ready! ✅
```

---

## ✅ Success Checklist

- [ ] Generated secure CRON_TOKEN
- [ ] Added CRON_TOKEN to Render environment variables
- [ ] Tested endpoint manually (got success response)
- [ ] Set up cron service (cron-job.org or similar)
- [ ] Verified first automated run (check logs next day)
- [ ] Set up email notifications for failures

---

## 🚨 Troubleshooting

**Problem:** Sync endpoint returns 401 Unauthorized
- **Fix:** Check CRON_TOKEN matches in Render environment and cron URL

**Problem:** Sync fails after starting
- **Fix:** Check Render logs for specific error
- **Common causes:** Cin7 API rate limits, network issues

**Problem:** No data updating
- **Fix:** Verify cron job is actually running (check cron service dashboard)

---

## 🎉 Once Set Up

Your database will:
- ✅ Automatically update stock levels daily
- ✅ Pull in new orders every day
- ✅ Stay current forever (no manual syncing needed!)
- ✅ Alert you if something breaks

**Set it and forget it!** 🚀

