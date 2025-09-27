-- Sync Service Database Migration
-- Run this to add sync tracking tables to your existing database

-- Sync logging table - tracks each sync operation
CREATE TABLE IF NOT EXISTS sync_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sync_type TEXT NOT NULL,           -- 'hourly', 'manual', 'backfill'
    started_at TEXT NOT NULL,
    completed_at TEXT,
    orders_processed INTEGER DEFAULT 0,
    lines_stored INTEGER DEFAULT 0,
    status TEXT DEFAULT 'running',     -- 'running', 'completed', 'failed'
    error_message TEXT,
    created_since_date TEXT,           -- What date we synced from
    total_api_calls INTEGER DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Note: sync_state table already exists with different structure, using it as-is

-- Initialize sync state with current position (June 11, 2025) if not exists
INSERT OR IGNORE INTO sync_state (sync_type, last_sync_timestamp, last_sync_success) 
VALUES ('hourly', '2025-06-11T00:00:00Z', 1);

-- Add index for better performance
CREATE INDEX IF NOT EXISTS idx_sync_log_started_at ON sync_log(started_at);
CREATE INDEX IF NOT EXISTS idx_sync_log_status ON sync_log(status);
CREATE INDEX IF NOT EXISTS idx_sync_state_sync_type ON sync_state(sync_type);

-- Insert initial sync log entry
INSERT OR IGNORE INTO sync_log 
(sync_type, started_at, completed_at, status, orders_processed, lines_stored, created_since_date)
VALUES 
('manual', '2025-06-11T00:00:00Z', '2025-06-11T00:00:00Z', 'completed', 0, 0, 'Initial setup - data synced to June 11, 2025');
