# Deployment Guide for Render

## Files Added for Deployment

1. **Procfile** - Tells Render how to run the app
2. **runtime.txt** - Specifies Python version
3. **Updated requirements.txt** - Added gunicorn for production
4. **Updated unified_stock_app.py** - Uses PORT environment variable

## Render Deployment Steps

### 1. Push to GitHub
```bash
git add .
git commit -m "Prepare for Render deployment"
git push origin main
```

### 2. Create Render Web Service
1. Go to [render.com](https://render.com) and sign in
2. Click "New" → "Web Service"
3. Connect your GitHub repository
4. Use these settings:
   - **Environment:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn unified_stock_app:app --bind 0.0.0.0:$PORT --workers 1 --timeout 120`

### 3. Set Environment Variables
In the Render dashboard, add these environment variables:

**Required:**
- `CIN7_ACCOUNT_ID` = your Cin7 account ID
- `CIN7_API_KEY` = your Cin7 API key
- `FLASK_ENV` = production

**Optional:**
- `CIN7_BASE_URL` = https://inventory.dearsystems.com/ExternalApi/v2 (default)
- `DATABASE_PATH` = /data/db/stock_forecast.db (if using custom path)

### 4. Deploy
Click "Create Web Service" - Render will:
1. Clone your repo
2. Install dependencies
3. Start the app with gunicorn
4. Provide a public URL

## Important Notes

### Database Persistence Options

#### Option 1: Persistent Disk with SQLite (Recommended)
1. In Render service settings, go to **"Disks"**
2. Add new disk:
   - **Mount Path:** `/data/db` (your current setup)
   - **Size:** 5GB (your current setup)
3. **No environment variable needed** - app auto-detects `/data/db`

#### Option 2: Render PostgreSQL
- Add Render PostgreSQL service
- More complex but better for high-traffic apps

#### Option 3: External Database
- Use external PostgreSQL/MySQL service
- Best for multi-service architectures

### First Time Setup
After deployment, you'll need to:
1. Visit `/sku-management` to select SKUs
2. Sync some data via the dashboard
3. Test the `/reorder` analysis

### Monitoring
- Check logs in Render dashboard
- Monitor performance and memory usage
- Set up alerts for failures

## Local Testing with Gunicorn

Test production setup locally:
```bash
# Install gunicorn if not already installed
pip install gunicorn

# Test with gunicorn (like production)
gunicorn unified_stock_app:app --bind 127.0.0.1:5050 --workers 1 --timeout 120
```

Visit http://localhost:5050 to test.

## Troubleshooting

### Common Issues:
1. **Import errors:** Check all dependencies in requirements.txt
2. **Database errors:** SQLite file not writable (expected on first run)
3. **API errors:** Check CIN7 environment variables
4. **Timeout errors:** Increase timeout in Procfile if needed

### Debug Mode:
- Never set `FLASK_ENV=development` in production
- Use Render logs to debug issues
- Test locally first with same environment variables
